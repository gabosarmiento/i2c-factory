# /agents/reflective/issue_resolution_operator.py
"""IssueResolutionOperator

A reflective agent for diagnosing failing tests, producing minimal patches, and
verifying the fixes – all while respecting i2c‑factory's token‑budget pipeline.
This version fixes the syntax/structural errors that prevented the original
module from importing.
"""

from __future__ import annotations

import difflib
import json
import re
import uuid
from pathlib import Path
from typing import Dict, List, Tuple

from agno.agent import Agent
from i2c.cli.controller import canvas
from builtins import llm_highest

from i2c.agents.sre_team import sandbox_executor
from i2c.agents.reflective.context_aware_operator import (
    ContextAwareOperator,
    ValidationHook,
    create_syntax_validation_hook,
)

################################################################################
# Main operator
################################################################################


class IssueResolutionOperator(ContextAwareOperator):
    """Diagnose a failing test, craft a minimal unified‑diff patch, and verify it."""

    def __init__(
        self,
        budget_manager,
        max_reasoning_steps: int = 3,
        **kwargs,
    ) -> None:
        super().__init__(
            budget_manager=budget_manager,
            operation_type="issue_resolution",
            max_reasoning_steps=max_reasoning_steps,
            default_model_tier="highest",
        )

        # Dedicated reasoning LLM
        self.reasoning_agent = Agent(
            model=llm_highest,
            reasoning=True,
            name="IssueResolutionAgent",
            description="Diagnoses and fixes code issues",
            instructions=[
                "You are an expert software debugger specialising in error resolution.",
                "Your goal is to diagnose and fix code issues by:",
                "1. Analysing error messages and stack traces carefully",
                "2. Identifying the root cause of failures",
                "3. Generating minimal, targeted patches to fix issues",
                "4. Validating that your fixes address the core problem",
                "Always create minimal patches that focus precisely on the root cause.",
            ],
        )

        self._register_default_validation_hooks()

    # ---------------------------------------------------------------------
    # Validation hooks
    # ---------------------------------------------------------------------

    def _register_default_validation_hooks(self) -> None:
        """Register patch‑level validation hooks (format + size)."""

        self.register_validation_hook(
            ValidationHook(
                hook_id="patch_format_validation",
                hook_type="patch_format",
                description="Validates that patches are properly formatted",
                validation_function=self._validate_patch_format,
                priority=9,
            )
        )

        self.register_validation_hook(
            ValidationHook(
                hook_id="patch_size_validation",
                hook_type="patch_size",
                description="Validates that patches are of reasonable size",
                validation_function=self._validate_patch_size,
                priority=8,
            )
        )

    ############################################################################
    # Public entry‑point
    ############################################################################

    def execute(  # noqa: C901 – complex but readable
        self,
        test_failure: Dict,
        file_content: str,
        file_path: str,
        language: str,
        project_path: Path,
    ) -> Tuple[bool, Dict]:
        """Run the full diagnose‑fix‑verify loop."""

        # ------------------------------------------------------------------
        # Phase 1 – analysis
        # ------------------------------------------------------------------
        phase_id = "analyze_failure"
        self.cost_tracker.start_phase(
            phase_id=phase_id,
            phase_description="Analyse test failure and identify root cause",
            model_id=getattr(llm_highest, "id", "Unknown"),
        )

        try:
            # Dynamic language‑specific syntax check
            self.register_validation_hook(create_syntax_validation_hook(language))

            analysis_prompt = self._prepare_analysis_prompt(
                test_failure, file_content, file_path, language
            )
            analysis_result = self._execute_reasoning_step(
                phase_id=phase_id,
                step_id="analyze_failure",
                prompt=analysis_prompt,
                model_tier="highest",
            )

            if not analysis_result:
                canvas.error("Failed to analyse test failure.")
                self.cost_tracker.end_phase(success=False, feedback="Failed to analyse test failure")
                return False, {"error": "Failed to analyse test failure"}

            failure_analysis = self._extract_analysis(analysis_result["response"])
            self.cost_tracker.end_phase(
                success=True,
                result=failure_analysis,
                feedback="Successfully analysed test failure",
            )

            # ------------------------------------------------------------------
            # Phase 2 – patch generation (with reflection loop)
            # ------------------------------------------------------------------
            phase_id = "generate_fix"
            self.cost_tracker.start_phase(
                phase_id=phase_id,
                phase_description="Generate fix for the identified issue",
                model_id=getattr(llm_highest, "id", "Unknown"),
            )

            fix_prompt = self._prepare_fix_prompt(
                failure_analysis, file_content, file_path, language
            )
            step_id = "generate_fix"
            fix_result = self._execute_reasoning_step(
                phase_id=phase_id,
                step_id=step_id,
                prompt=fix_prompt,
                model_tier="highest",
            )
            if not fix_result:
                canvas.error("Failed to generate fix.")
                self.cost_tracker.end_phase(success=False, feedback="Failed to generate fix")
                return False, {"error": "Failed to generate fix"}

            patch = self._extract_patch(fix_result["response"]) or self._create_unified_diff_from_blocks(
                fix_result["response"], file_content
            )
            if not patch:
                canvas.warning("No patch found in fix generation response.")
                self.cost_tracker.end_phase(success=False, feedback="No patch found in response")
                return False, {"error": "No patch found in response"}

            fixed_content = self._apply_patch(file_content, patch)

            # -------------------------- validation loop --------------------
            validation_results: Dict[str, Dict] = {}
            iterations = 1
            valid_fix = False

            while iterations <= self.max_reasoning_steps:
                # 1️⃣ run validations
                validation_results.clear()
                for hook_id, hook in self.validation_hooks.items():
                    target = fixed_content if hook.hook_type == "syntax" else patch
                    outcome, feedback = hook.validate(target)
                    validation_results[hook_id] = {"outcome": outcome, "feedback": feedback}

                valid_fix = all(r["outcome"] for r in validation_results.values())
                self.cost_tracker.record_validation(
                    step_id=f"validation_{iterations}",
                    outcome=valid_fix,
                    feedback=json.dumps(validation_results, indent=2),
                )
                if valid_fix or iterations == self.max_reasoning_steps:
                    break

                # 2️⃣ improve patch
                improve_prompt = self._prepare_improve_prompt(
                    failure_analysis,
                    patch,
                    fixed_content,
                    validation_results,
                    file_content,
                    file_path,
                    language,
                )
                improve_result = self._execute_reasoning_step(
                    phase_id=phase_id,
                    step_id=f"improve_fix_{iterations}",
                    prompt=improve_prompt,
                    model_tier="highest",
                )
                if not improve_result:
                    canvas.error(f"Failed to improve fix on iteration {iterations}.")
                    break

                patch = self._extract_patch(improve_result["response"]) or self._create_unified_diff_from_blocks(
                    improve_result["response"], file_content
                )
                if not patch:
                    canvas.warning(f"No patch found in iteration {iterations}.")
                    break

                fixed_content = self._apply_patch(file_content, patch)
                iterations += 1

            self.cost_tracker.end_phase(
                success=valid_fix,
                result={"patch": patch, "fixed_content": fixed_content},
                feedback=f"Fix validation: {valid_fix}",
            )

            # ------------------------------------------------------------------
            # Phase 3 – verify by running tests
            # ------------------------------------------------------------------
            phase_id = "verify_fix"
            self.cost_tracker.start_phase(
                phase_id=phase_id,
                phase_description="Verify fix by running tests",
                model_id=getattr(llm_highest, "id", "Unknown"),
            )

            test_success = False
            test_output = "Test verification not implemented"
            if valid_fix and sandbox_executor and hasattr(sandbox_executor, "verify_fix"):
                from tempfile import TemporaryDirectory

                try:
                    with TemporaryDirectory() as tmp:
                        tmp_path = Path(tmp)
                        target = tmp_path / file_path
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_text(fixed_content)

                        # In a real implementation we'd copy the entire project, but the
                        # sandbox_executor is assumed to handle a minimal context.
                        test_success, test_output = sandbox_executor.verify_fix(
                            tmp_path, file_path, test_failure
                        )
                except Exception as exc:  # pragma: no cover – sandbox issues
                    canvas.error(f"Error verifying fix: {exc}")
                    test_output = f"Error verifying fix: {exc}"

            self.cost_tracker.end_phase(
                success=test_success,
                result={"test_success": test_success, "test_output": test_output},
                feedback=f"Test verification: {test_success}",
            )

            # ------------------------------------------------------------------
            # Wrap‑up
            # ------------------------------------------------------------------
            final_result = {
                "original_content": file_content,
                "fixed_content": fixed_content,
                "patch": patch,
                "validation": valid_fix,
                "test_verification": test_success,
                "test_output": test_output,
                "iterations": iterations,
                "reasoning_trajectory": self.cost_tracker.trajectory,
            }
            success = valid_fix and test_success
            self.cost_tracker.complete_operation(success=success, final_result=final_result)
            return success, final_result

        # ------------------------------------------------------------------
        # Any unhandled exception…
        # ------------------------------------------------------------------
        except Exception as exc:  # noqa: BLE001
            canvas.error(f"Error in issue resolution: {exc}")
            self.cost_tracker.complete_operation(success=False, final_result={"error": str(exc)})
            return False, {"error": str(exc)}

    ############################################################################
    # Prompt helpers
    ############################################################################

    def _prepare_analysis_prompt(
        self,
        test_failure: Dict,
        file_content: str,
        file_path: str,
        language: str,
    ) -> str:
        """Craft the LLM prompt for the analysis step."""

        error_type = test_failure.get("error_type", "Unknown")
        error_message = test_failure.get("error_message", "")
        traceback = test_failure.get("traceback", "")
        failing_test = test_failure.get("failing_test", "")

        line_numbers = self._extract_line_numbers(traceback)
        code_snippets = self._extract_code_snippets(file_content, line_numbers)
        formatted_snippets = self._format_code_snippets(code_snippets)

        return f"""
# Issue Analysis Task

## Test Failure Information
Error Type: {error_type}
Error Message: {error_message}

## Traceback
```
{traceback}
```

## Failing Test
```
{failing_test}
```

## Code Snippets Around Error
{formatted_snippets}

## Full File Content
```{language}
{file_content}
```

## Analysis Task
Please analyse this test failure carefully, looking for:
1. The root cause of the failure
2. The specific lines of code causing the issue
3. The logic or syntax error that needs to be fixed
4. Any context from the file that's important to understand the issue

Return a structured analysis with these sections:
- Root Cause Identification
- Affected Code Explanation
- Fix Approach
- Potential Side Effects

Think step by step and be specific about exactly what's causing the issue.
"""

    def _prepare_fix_prompt(
        self,
        analysis: Dict,
        file_content: str,
        file_path: str,
        language: str,
    ) -> str:
        """Craft the prompt that asks the LLM to propose a patch."""

        analysis_text = ""
        for section, content in (analysis.get("sections") or {}).items():
            if isinstance(content, list):
                section_text = "\n".join(f"- {item}" for item in content)
            else:
                section_text = str(content)
            analysis_text += f"### {section.replace('_', ' ').title()}\n{section_text}\n\n"

        return f"""
# Issue Fix Task

## File Path
{file_path}

## Issue Analysis
{analysis_text}

## Original Code
```{language}
{file_content}
```

## Fix Task
Based on the analysis, create a fix that:
1. Addresses the root cause of the issue
2. Makes minimal changes to the code
3. Preserves the original functionality
4. Follows the code style of the original file

Provide your fix in two formats:
1. A unified diff patch (with - for removed lines, + for added lines)
2. The complete fixed version of the code
"""

    def _prepare_improve_prompt(
        self,
        analysis: Dict,
        patch: str,
        fixed_content: str,
        validation_results: Dict,
        original_content: str,
        file_path: str,
        language: str,
    ) -> str:
        """Prompt for a second pass when validations fail."""

        validation_feedback = "\n".join(
            f"- {hook_id}: {'✅' if res['outcome'] else '❌'} {res['feedback']}"
            for hook_id, res in validation_results.items()
            if not res["outcome"]
        )

        return f"""
# Fix Improvement Task

## File Path
{file_path}

## Validation Issues
{validation_feedback}

## Current Patch
```diff
{patch}
```

## Current Fixed Code
```{language}
{fixed_content}
```

## Original Code
```{language}
{original_content}
```

## Improvement Task
Please improve the fix to address all validation issues. Your improved fix should:
1. Pass syntax validation for {language}
2. Be properly formatted as a unified diff
3. Make minimal, targeted changes

Provide your improved fix in the same format as before.
"""

    ############################################################################
    # Extraction helpers
    ############################################################################

    def _extract_analysis(self, response: str) -> Dict:
        """Pull structured analysis sections out of the LLM response."""

        sections: Dict[str, List[str]] = {}
        current: str | None = None

        for line in response.splitlines():
            striped = line.strip()
            if not striped:
                continue

            if striped.startswith(("##", "###")) or any(
                striped.lower().startswith(prefix)
                for prefix in ("root cause", "fix approach")
            ):
                current = (
                    striped.lstrip("# ").split(":")[0].lower().replace(" ", "_")
                )
                sections[current] = []
            elif current:
                sections[current].append(striped)

        if sections:
            return {"sections": sections, "structured": True}
        return {"analysis": response, "structured": False}

    def _extract_patch(self, response: str) -> str:
        """Return the first diff‑style block found inside *response*."""

        patch_lines, in_diff, has_markers = [], False, False
        for line in response.splitlines():
            if line.strip().startswith("```diff"):
                in_diff = True
                continue
            if in_diff and line.strip().startswith("```"):
                in_diff = False
                if has_markers:
                    return "\n".join(patch_lines)
                patch_lines, has_markers = [], False
                continue
            if in_diff:
                patch_lines.append(line)
                if line.lstrip().startswith(("+", "-", "@@")):
                    has_markers = True

        # Fallback: any diffy lines at all?
        if not patch_lines:
            for line in response.splitlines():
                if line.lstrip().startswith(("+", "-", "@@")):
                    patch_lines.append(line)
                    has_markers = True
                elif patch_lines and has_markers:
                    patch_lines.append(line)
        return "\n".join(patch_lines) if has_markers else ""

    def _create_unified_diff_from_blocks(
        self, response: str, original_content: str
    ) -> str:
        """Fallback when the LLM provides before/after code blocks instead of a diff."""
        """The (?i) makes the match case‑insensitive, so “before:”/“Before:” both work."""
        before = re.search(r"(?i)(?:before|original):?\s*```(?:\w+)?\s*([\s\S]*?)```", response,re.VERBOSE,)
        after  = re.search(r"(?i)(?:after|fixed):?\s*```(?:\w+)?\s*([\s\S]*?)```",  response,re.VERBOSE,)
        
        # ── 2. build diff if we found both  ────────────────────────────────────
        if before and after:
            before_code = before.group(1).strip() or original_content
            after_code  = after.group(1).strip()
            diff = difflib.unified_diff(
                before_code.splitlines(),
                after_code.splitlines(),
                fromfile="original",
                tofile="fixed",
                lineterm="",
            )
            return "\n".join(diff)

        # If only a large code block is provided, diff it against the original
        blocks = list(re.finditer(r"```(?:\w+)?\s*([\s\S]*?)```", response))
        if blocks:
            full_code = max(blocks, key=lambda m: len(m.group(1))).group(1).rstrip()
            if full_code and full_code != original_content:
                return "\n".join(
                    difflib.unified_diff(
                        original_content.splitlines(),
                        full_code.splitlines(),
                        fromfile="original",
                        tofile="fixed",
                        lineterm="",
                    )
                )
        return ""

    def _apply_patch(self, original_content: str, patch: str) -> str:  # pragma: no cover – simple
        """Very naive patch application (prefers *unidiff* if available)."""

        try:
            from io import StringIO

            from unidiff import PatchSet  # type: ignore

            patched = original_content.splitlines()
            for hunk in PatchSet(StringIO(patch))[0]:
                start = hunk.source_start - 1
                removed = sum(1 for l in hunk if l.is_removed)
                additions = [l.value for l in hunk if l.is_added]
                patched = patched[:start] + additions + patched[start + removed :]
            return "\n".join(patched)
        except ImportError:
            canvas.warning("unidiff not available – using fallback patch application")
        except Exception as exc:
            canvas.error(f"Patch application failed: {exc}")
        return original_content  # fallback – return untouched code

    ############################################################################
    # Misc helpers
    ############################################################################

    @staticmethod
    def _extract_line_numbers(traceback: str) -> List[int]:
        return [int(num) for num in re.findall(r"line\s+(\d+)", traceback)]

    @staticmethod
    def _extract_code_snippets(code: str, lines: List[int]) -> Dict[int, str]:
        snippets: Dict[int, str] = {}
        src = code.splitlines()
        for ln in lines:
            idx = ln - 1
            start, end = max(0, idx - 3), min(len(src), idx + 4)
            snippet = "\n".join(
                f"{i + 1}{' >>>' if i == idx else '    '} {src[i]}" for i in range(start, end)
            )
            snippets[ln] = snippet
        return snippets

    @staticmethod
    def _format_code_snippets(snippets: Dict[int, str]) -> str:
        if not snippets:
            return "No relevant code snippets available."
        return "\n\n".join(f"### Around Line {ln}:\n```\n{blk}\n```" for ln, blk in snippets.items())

    # ------------------------------------------------------------------
    # Patch‑level validators
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_patch_format(patch: str) -> Tuple[bool, str]:
        if not patch:
            return False, "Patch is empty."
        if not any(line.lstrip().startswith(('+', '-')) for line in patch.splitlines()):
            return False, "Patch doesn't contain any additions (+) or removals (-)."
        return True, "Patch format is valid."

    @staticmethod
    def _validate_patch_size(patch: str) -> Tuple[bool, str]:
        if not patch:
            return False, "Patch is empty."
        adds = sum(1 for l in patch.splitlines() if l.lstrip().startswith('+'))
        dels = sum(1 for l in patch.splitlines() if l.lstrip().startswith('-'))
        if adds + dels > 20:
            return (
                False,
                f"Patch is too large: {adds} additions, {dels} removals (max 20 total)",
            )
        return True, f"Patch size is reasonable: {adds} additions, {dels} removals."
