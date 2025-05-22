# src/i2c/bootstrap.py
import os
import builtins
from pathlib import Path
from i2c.llm_providers import initialize_groq_providers

# Compute and inject PROJECT_ROOT
PROJECT_ROOT = Path(__file__).parents[2].resolve()
builtins.PROJECT_ROOT = PROJECT_ROOT

def initialize_environment():
    """
    1) Disable tokenizer parallelism.
    2) Initialize Groq LLM providers.
    3) Ensure our LanceDB tables exist before any agent imports.
    """
    # 1) Tokenizer safety
     
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    builtins.llm_highest, builtins.llm_middle, builtins.llm_middle_alt, builtins.llm_small, builtins.llm_deepseek, builtins.llm_ligthweight = initialize_groq_providers()

    # 2) Initialize a global budget manager if not already present
    if not hasattr(builtins, 'global_budget_manager'):
        from i2c.agents.budget_manager import BudgetManagerAgent
        builtins.global_budget_manager = BudgetManagerAgent(session_budget=10.0)
        
    # 3) Auto-create/migrate our tables *here*, before any agent loads
    from i2c.db_utils import (
        get_db_connection,
        get_or_create_table,
        TABLE_CODE_CONTEXT,
        SCHEMA_CODE_CONTEXT,
        TABLE_KNOWLEDGE_BASE,
        SCHEMA_KNOWLEDGE_BASE,
    )
    db = get_db_connection()
    get_or_create_table(db, TABLE_CODE_CONTEXT,   SCHEMA_CODE_CONTEXT)
    get_or_create_table(db, TABLE_KNOWLEDGE_BASE, SCHEMA_KNOWLEDGE_BASE)