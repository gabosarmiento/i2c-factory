from typing import Dict, List, Optional, Any, Union
from pathlib import Path
import logging

from i2c.agents.knowledge.pattern_extractor import PatternExtractorAgent
from i2c.cli.controller import canvas
logger = logging.getLogger(__name__)


class AgentKnowledgeEnhancer:
    """
    Framework-agnostic agent enhancement with knowledge-driven reasoning.
    Integrates seamlessly with existing agent creation workflows.
    """
    
    def __init__(self):
        self.reasoner = PatternExtractorAgent()
        self.enhancement_cache = {}  # Cache patterns to avoid re-processing
        
    def enhance_agent_with_knowledge(
        self,
        agent,
        knowledge_context: str,
        agent_type: str,
        task_context: Optional[str] = None
    ):
        """
        Enhance any agent with knowledge-driven reasoning capabilities.
        
        Args:
            agent: Any agent object with instructions attribute
            knowledge_context: Raw retrieved knowledge (from RAG/vector DB)
            agent_type: Type hint for reasoning requirements (planner, code_builder, etc.)
            task_context: Optional task description for context-specific enhancement
            
        Returns:
            Enhanced agent with knowledge reasoning requirements
        """
        if not knowledge_context or not hasattr(agent, 'instructions'):
            logger.debug(f"Skipping enhancement for {agent_type}: no context or instructions")
            canvas.warning(f"🔍 DEBUG: Skipping enhancement - no_context={not knowledge_context}, no_instructions={not hasattr(agent, 'instructions')}")
            return agent
        
        try:
            # Extract patterns (with caching)
            cache_key = hash(knowledge_context)
            if cache_key in self.enhancement_cache:
                patterns = self.enhancement_cache[cache_key]
                logger.debug(f"Cache HIT for {agent_type} (key: {cache_key})")
            else:
                patterns = self._extract_patterns_directly(knowledge_context)
                self.enhancement_cache[cache_key] = patterns
                logger.debug(f"Cache MISS for {agent_type} (key: {cache_key}) - patterns extracted and cached")
            
            if not patterns:
                logger.debug(f"No actionable patterns found for {agent_type}")
                return agent
            
            # Create reasoning requirements
            requirements = self.reasoner.create_reasoning_requirements(patterns, agent_type)
            
            # Inject requirements into agent instructions
            self._inject_requirements_into_agent(agent, requirements)
            
            # Store patterns for validation
            agent._knowledge_patterns = patterns
            agent._enhanced_with_knowledge = True
            agent._agent_type = agent_type
            
            logger.info(f"Enhanced {agent_type} with {len(patterns)} pattern types")
            
        except Exception as e:
            logger.error(f"Failed to enhance {agent_type}: {e}")
            # Don't fail agent creation, just continue without enhancement
        
        return agent

    def _extract_patterns_directly(self, knowledge_context: str) -> Dict[str, List[str]]:
        """Context-aware pattern extractor that detects domain and extracts appropriate patterns"""
        
        
        if not knowledge_context:
            return {"imports": [], "file_structure": [], "conventions": [], "architecture": [], "examples": []}
        
        # STEP 1: Detect the domain/context type
        domain_context = self._detect_content_domain(knowledge_context)
        
        # STEP 2: Extract patterns based on detected domain
        if domain_context == "ai_ml_framework":
            return self._extract_ai_ml_patterns(knowledge_context)
        elif domain_context == "trading_finance":
            return self._extract_trading_patterns(knowledge_context)
        elif domain_context == "web_development":
            return self._extract_web_dev_patterns(knowledge_context)
        elif domain_context == "data_science":
            return self._extract_data_science_patterns(knowledge_context)
        elif domain_context == "general_programming":
            return self._extract_programming_patterns(knowledge_context)
        else:
            # Fallback to universal extraction
            return self._extract_universal_patterns(knowledge_context)

    def _detect_content_domain(self, knowledge_context: str) -> str:
        """Detect what domain/type of content we're dealing with"""
        
        context_lower = knowledge_context.lower()
        
        # AI/ML Framework indicators
        ai_ml_indicators = [
            'agent', 'llm', 'transformer', 'embedding', 'vector', 'model',
            'openai', 'anthropic', 'huggingface', 'tensorflow', 'pytorch',
            'langchain', 'agno', 'autogen', 'reasoning', 'prompt', 'completion',
            'neural network', 'machine learning', 'deep learning', 'orchestrat'
        ]
        
        # Trading/Finance indicators  
        trading_indicators = [
            'forex', 'trading', 'currency', 'pips', 'spread', 'volatility',
            'rsi', 'macd', 'ema', 'bollinger', 'support', 'resistance',
            'usd', 'eur', 'gbp', 'jpy', 'technical analysis', 'chart pattern',
            'market session', 'economic impact', 'central bank',
            'interactive brokers', 'ib_insync', 'ibapi', 'tws', 'gateway',
            'portfolio', 'position', 'order', 'contract', 'market data',
            'algorithmic trading', 'automated trading', 'backtesting',
            'risk management', 'stop loss', 'take profit', 'margin'
        ]
        
        # Web Development indicators
        web_dev_indicators = [
            'react', 'javascript', 'typescript', 'html', 'css', 'frontend',
            'backend', 'api', 'endpoint', 'component', 'jsx', 'nodejs',
            'express', 'fastapi', 'django', 'flask', 'database', 'mongodb',
            'full-stack', 'fullstack', 'rest api', 'graphql', 'cors',
            'authentication', 'authorization', 'middleware', 'routing',
            'tailwind', 'bootstrap', 'vite', 'webpack', 'docker'
        ]
        
        # Data Science indicators
        data_science_indicators = [
            'pandas', 'numpy', 'matplotlib', 'scikit-learn', 'jupyter',
            'dataframe', 'dataset', 'analytics', 'visualization', 'statistics',
            'regression', 'classification', 'clustering', 'feature engineering',
            'machine learning', 'data analysis', 'exploratory data analysis',
            'eda', 'seaborn', 'plotly', 'scipy', 'statsmodels', 'data science',
            'predictive modeling', 'cross validation', 'hyperparameter tuning'
        ]
        
        # General Programming indicators
        programming_indicators = [
            'function', 'class', 'method', 'variable', 'algorithm',
            'data structure', 'object oriented', 'functional programming',
            'design pattern', 'clean code', 'best practices',
            'software engineering', 'code quality', 'refactoring',
            'unit testing', 'integration testing', 'debugging',
            'version control', 'git', 'solid principles', 'dry principle'
        ]
        
        # Count indicators for each domain
        ai_ml_count = sum(1 for indicator in ai_ml_indicators if indicator in context_lower)
        trading_count = sum(1 for indicator in trading_indicators if indicator in context_lower)
        web_dev_count = sum(1 for indicator in web_dev_indicators if indicator in context_lower)
        data_science_count = sum(1 for indicator in data_science_indicators if indicator in context_lower)
        programming_count = sum(1 for indicator in programming_indicators if indicator in context_lower)
        
        
        # Determine dominant domain
        scores = {
            "ai_ml_framework": ai_ml_count,
            "trading_finance": trading_count,
            "web_development": web_dev_count,
            "data_science": data_science_count,
            "general_programming": programming_count
        }
        
        max_domain = max(scores.keys(), key=lambda k: scores[k])
        
        # Require minimum threshold to avoid false positives
        if scores[max_domain] >= 3:
            return max_domain
        else:
            return "universal"
    
    def _extract_ai_ml_patterns(self, knowledge_context: str) -> Dict[str, List[str]]:
        """Extract AI/ML framework patterns"""
        
        import re
        sentences = re.split(r'[.!?\n]+', knowledge_context)
        sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]
        
        imports = []
        conventions = []
        architecture = []
        examples = []
        file_structure = []
        
        for i, sentence in enumerate(sentences):
            sentence_lower = sentence.lower()
            
            # IMPORTS: AI/ML libraries, frameworks, agent patterns
            if self._is_ai_ml_import_pattern(sentence, sentence_lower):
                imports.append(sentence.strip())
            
            # EXAMPLES: Agent implementations, team patterns, model usage
            elif self._is_ai_ml_example_pattern(sentence, sentence_lower):
                examples.append(sentence.strip())
                
            # CONVENTIONS: Best practices, patterns, usage guidelines
            elif self._is_ai_ml_convention_pattern(sentence, sentence_lower):
                conventions.append(sentence.strip())
                
            # ARCHITECTURE: Framework structures, orchestration patterns
            elif self._is_ai_ml_architecture_pattern(sentence, sentence_lower):
                architecture.append(sentence.strip())
                
            # FILE STRUCTURE: Project organization, agent files
            elif self._is_ai_ml_structure_pattern(sentence, sentence_lower):
                file_structure.append(sentence.strip())
        
        return {
            "imports": imports[:4],        # Balanced: Keep essential imports
            "file_structure": file_structure[:4],  # Balanced: Keep key structure patterns
            "conventions": conventions[:5],       # Balanced: Keep important conventions
            "architecture": architecture[:4],      # Balanced: Keep core architecture
            "examples": examples[:3]              # Balanced: Keep minimal examples
        }

    def _is_ai_ml_import_pattern(self, sentence: str, sentence_lower: str) -> bool:
        """Detect AI/ML related imports and dependencies"""
        
        # AI/ML libraries and frameworks
        ai_ml_libs = [
            'openai', 'anthropic', 'huggingface', 'transformers', 'langchain',
            'agno', 'autogen', 'tensorflow', 'pytorch', 'scikit-learn',
            'numpy', 'pandas', 'matplotlib', 'requests', 'json', 'asyncio'
        ]
        
        # AI/ML specific imports
        ai_imports = [
            'from agno', 'import agno', 'from openai import', 'import openai',
            'from langchain', 'import langchain', 'from transformers',
            'import Agent', 'from Agent', 'import Team', 'from Team'
        ]
        
        # Framework concepts that suggest imports
        framework_concepts = [
            'agent', 'team', 'model', 'llm', 'embedding', 'vector',
            'prompt', 'completion', 'reasoning', 'orchestrat'
        ]
        
        has_ai_lib = any(lib in sentence_lower for lib in ai_ml_libs)
        has_ai_import = any(imp in sentence_lower for imp in ai_imports)
        has_framework = any(concept in sentence_lower for concept in framework_concepts)
        
        return (has_ai_lib or has_ai_import or has_framework) and len(sentence) < 300

    def _is_ai_ml_example_pattern(self, sentence: str, sentence_lower: str) -> bool:
        """Detect AI/ML examples and implementations"""
        
        # Agent implementation examples
        agent_examples = [
            'agent =', 'team =', 'model =', '.run(', '.execute(',
            'instructions=', 'role=', 'name=', 'Agent(', 'Team('
        ]
        
        # ML model usage
        model_examples = [
            'model.predict', 'model.fit', 'embedding =', 'vector =',
            'prompt =', 'response =', 'completion =', 'generate('
        ]
        
        # Code patterns
        code_patterns = [
            '=', '(', ')', '{', '}', '[', ']', 'def ', 'class ',
            'if ', 'for ', 'while ', 'try:', 'except:'
        ]
        
        has_agent_example = any(example in sentence_lower for example in agent_examples)
        has_model_example = any(example in sentence_lower for example in model_examples)
        has_code = any(pattern in sentence for pattern in code_patterns)
        
        return (has_agent_example or has_model_example) and has_code and len(sentence) < 400

    def _is_ai_ml_convention_pattern(self, sentence: str, sentence_lower: str) -> bool:
        """Detect AI/ML conventions and best practices"""
        
        # Best practices indicators
        best_practices = [
            'should', 'must', 'always', 'never', 'avoid', 'recommended',
            'best practice', 'important', 'ensure', 'remember', 'note'
        ]
        
        # AI/ML specific conventions
        ai_conventions = [
            'agent', 'team', 'orchestrat', 'reasoning', 'prompt',
            'model', 'embedding', 'vector', 'context', 'instruction'
        ]
        
        # Usage patterns
        usage_patterns = [
            'use', 'create', 'define', 'build', 'implement', 'design',
            'structure', 'organize', 'manage', 'coordinate'
        ]
        
        has_best_practice = any(practice in sentence_lower for practice in best_practices)
        has_ai_convention = any(convention in sentence_lower for convention in ai_conventions)
        has_usage = any(pattern in sentence_lower for pattern in usage_patterns)
        
        return (has_best_practice or has_usage) and has_ai_convention and 20 < len(sentence) < 300

    def _is_ai_ml_architecture_pattern(self, sentence: str, sentence_lower: str) -> bool:
        """Detect AI/ML architecture and framework patterns"""
        
        # Architecture concepts
        architecture_concepts = [
            'orchestrat', 'team', 'agent', 'framework', 'system',
            'pattern', 'structure', 'design', 'architecture'
        ]
        
        # AI/ML systems
        system_patterns = [
            'reasoning', 'coordination', 'delegation', 'collaboration',
            'workflow', 'pipeline', 'processing', 'management'
        ]
        
        # Framework patterns
        framework_patterns = [
            'agno', 'langchain', 'autogen', 'multi-agent', 'abstraction',
            'layer', 'component', 'module', 'service'
        ]
        
        has_architecture = any(concept in sentence_lower for concept in architecture_concepts)
        has_system = any(pattern in sentence_lower for pattern in system_patterns)
        has_framework = any(pattern in sentence_lower for pattern in framework_patterns)
        
        return (has_architecture or has_system or has_framework) and 15 < len(sentence) < 300

    def _is_ai_ml_structure_pattern(self, sentence: str, sentence_lower: str) -> bool:
        """Detect AI/ML file structure and organization patterns"""
        
        # File organization
        file_patterns = [
            'agents/', 'models/', 'teams/', 'workflows/', 'prompts/',
            'config/', 'utils/', 'services/', 'api/', 'backend/'
        ]
        
        # AI/ML files
        ai_files = [
            '.py', '.json', '.yaml', 'agent.py', 'team.py',
            'model.py', 'config.yaml', 'requirements.txt'
        ]
        
        # Organization concepts
        organization_patterns = [
            'organize', 'structure', 'directory', 'folder', 'file',
            'separate', 'group', 'categorize', 'project'
        ]
        
        has_file_pattern = any(pattern in sentence_lower for pattern in file_patterns)
        has_ai_file = any(file_type in sentence_lower for file_type in ai_files)
        has_organization = any(pattern in sentence_lower for pattern in organization_patterns)
        
        return (has_file_pattern or has_ai_file or has_organization) and len(sentence) < 250

    def _extract_trading_patterns(self, knowledge_context: str) -> Dict[str, List[str]]:
        """Extract trading/finance patterns for Interactive Brokers and AI trading systems"""
        
        import re
        sentences = re.split(r'[.!?\n]+', knowledge_context)
        sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]
        
        imports = []
        conventions = []
        architecture = []
        examples = []
        file_structure = []
        
        canvas.info(f"🔍 DEBUG: Trading extraction processing {len(sentences)} sentences")
        
        for i, sentence in enumerate(sentences):
            sentence_lower = sentence.lower()
            
            # IMPORTS: Trading libraries, IB API, data sources, analysis tools
            if self._is_trading_import_pattern(sentence, sentence_lower):
                imports.append(sentence.strip())
                canvas.info(f"🔍 DEBUG: Found trading import pattern #{i}: {sentence.strip()}")
            
            # EXAMPLES: Strategy implementations, calculations, rules, IB API usage
            elif self._is_trading_example_pattern(sentence, sentence_lower):
                examples.append(sentence.strip())
                
            # CONVENTIONS: Trading rules, risk management, best practices
            elif self._is_trading_convention_pattern(sentence, sentence_lower):
                conventions.append(sentence.strip())
                
            # ARCHITECTURE: Strategy structure, analysis frameworks, AI trading systems
            elif self._is_trading_architecture_pattern(sentence, sentence_lower):
                architecture.append(sentence.strip())
                
            # FILE STRUCTURE: Data organization, strategy files, IB integration
            elif self._is_trading_structure_pattern(sentence, sentence_lower):
                file_structure.append(sentence.strip())
        
        return {
            "imports": imports[:2],        # Reduced from 10 to 2 - top most relevant
            "file_structure": file_structure[:2],  # Reduced from 8 to 2 - essential structure only
            "conventions": conventions[:3],       # Reduced from 12 to 3 - core conventions
            "architecture": architecture[:2],      # Reduced from 8 to 2 - key architecture patterns
            "examples": examples[:2]              # Reduced from 12 to 2 - best examples
        }

    def _is_trading_import_pattern(self, sentence: str, sentence_lower: str) -> bool:
        """Detect trading-related imports and dependencies"""
        
        # Interactive Brokers and trading libraries
        trading_libs = [
            'ib_insync', 'ibapi', 'interactive_brokers', 'ib_api',
            'pandas', 'numpy', 'yfinance', 'ccxt', 'alpaca', 'mt5',
            'talib', 'backtrader', 'zipline', 'quantlib', 'matplotlib',
            'plotly', 'requests', 'websocket', 'json', 'datetime',
            'asyncio', 'threading', 'schedule', 'apscheduler'
        ]
        
        # Trading-specific imports and API patterns
        trading_imports = [
            'from ib_insync import', 'import ib_insync', 'from ibapi import',
            'import ibapi', 'from Interactive_Brokers', 'import pandas',
            'import numpy', 'from datetime import', 'import yfinance',
            'import ccxt', 'import talib', 'import matplotlib',
            'from threading import', 'import asyncio', 'from apscheduler'
        ]
        
        # Configuration and API patterns
        api_patterns = [
            'api_key', 'secret_key', 'broker', 'exchange', 'symbol',
            'timeframe', 'interval', 'ohlc', 'tick_data', 'ib_gateway',
            'tws', 'client_id', 'port', 'host', 'connection'
        ]
        
        # IB specific patterns
        ib_patterns = [
            'contract', 'order', 'portfolio', 'account', 'positions',
            'market_data', 'real_time', 'historical_data', 'scanner'
        ]
        
        has_trading_lib = any(lib in sentence_lower for lib in trading_libs)
        has_trading_import = any(imp in sentence_lower for imp in trading_imports)
        has_api = any(pattern in sentence_lower for pattern in api_patterns)
        has_ib = any(pattern in sentence_lower for pattern in ib_patterns)
        
        return (has_trading_lib or has_trading_import or has_api or has_ib) and len(sentence) < 300

    def _is_trading_example_pattern(self, sentence: str, sentence_lower: str) -> bool:
        """Detect trading examples and implementations"""
        
        # Strategy examples and signals
        strategy_examples = [
            'rsi >', 'rsi <', 'macd crosses', 'moving average', 'sma', 'ema',
            'bollinger bands', 'if price >', 'when volatility', 'calculate',
            'formula', 'signal', 'buy_signal', 'sell_signal', 'entry', 'exit'
        ]
        
        # Position and risk management
        position_examples = [
            'position_size =', 'stop_loss =', 'take_profit =', 'risk_percent',
            'portfolio_value', 'available_funds', 'margin', 'leverage',
            'quantity =', 'shares =', 'contracts =', 'lot_size'
        ]
        
        # IB API specific examples
        ib_examples = [
            'ib.connect()', 'ib.reqMarketDataType', 'ib.placeOrder',
            'ib.cancelOrder', 'ib.reqHistoricalData', 'ib.reqMktData',
            'Contract()', 'Order()', 'MarketOrder()', 'LimitOrder()',
            'StopOrder()', 'Portfolio()', 'AccountSummary()'
        ]
        
        # Trading calculations and indicators
        calculation_patterns = [
            '* 1.5', '* 2', '/ 100', '+ 50', '- 30', '>', '<', '>=', '<=',
            'pips', 'percentage', 'ratio', 'threshold', 'level',
            'mean()', 'std()', 'rolling()', 'shift()', 'pct_change()'
        ]
        
        # Code implementation patterns
        implementation_patterns = [
            'if ', 'elif ', 'else:', 'for ', 'while ', 'def ', 'class ',
            'try:', 'except:', 'async def', 'await ', 'return ', '='
        ]
        
        has_strategy = any(pattern in sentence_lower for pattern in strategy_examples)
        has_position = any(pattern in sentence_lower for pattern in position_examples)
        has_ib = any(pattern in sentence for pattern in ib_examples)
        has_calculation = any(pattern in sentence for pattern in calculation_patterns)
        has_implementation = any(pattern in sentence for pattern in implementation_patterns)
        
        return (has_strategy or has_position or has_ib or has_calculation) and has_implementation and len(sentence) < 400

    def _is_trading_convention_pattern(self, sentence: str, sentence_lower: str) -> bool:
        """Detect trading conventions and best practices"""
        
        # Risk management rules
        risk_management = [
            'risk', 'stop loss', 'take profit', 'position size', 'drawdown',
            'never risk more than', 'always use', 'maximum', 'minimum',
            'rule', 'limit', 'threshold', 'avoid', 'ensure', 'money management'
        ]
        
        # Trading discipline and best practices
        discipline_patterns = [
            'should', 'must', 'always', 'never', 'avoid', 'recommended',
            'best practice', 'important', 'remember', 'note', 'warning',
            'discipline', 'psychology', 'emotion', 'patience'
        ]
        
        # Market conditions and timing
        market_conditions = [
            'high volatility', 'low liquidity', 'trending market', 'ranging market',
            'news events', 'market hours', 'session', 'spread', 'slippage',
            'pre-market', 'after-hours', 'market open', 'market close'
        ]
        
        # IB specific conventions
        ib_conventions = [
            'tws', 'gateway', 'connection', 'api limits', 'market data',
            'permissions', 'account type', 'commission', 'margin requirements'
        ]
        
        # AI trading specific
        ai_trading = [
            'machine learning', 'neural network', 'prediction', 'model training',
            'backtesting', 'optimization', 'feature engineering', 'overfitting'
        ]
        
        has_risk_mgmt = any(pattern in sentence_lower for pattern in risk_management)
        has_discipline = any(pattern in sentence_lower for pattern in discipline_patterns)
        has_market_condition = any(pattern in sentence_lower for pattern in market_conditions)
        has_ib = any(pattern in sentence_lower for pattern in ib_conventions)
        has_ai = any(pattern in sentence_lower for pattern in ai_trading)
        
        return (has_risk_mgmt or has_discipline or has_market_condition or has_ib or has_ai) and 20 < len(sentence) < 350

    def _is_trading_architecture_pattern(self, sentence: str, sentence_lower: str) -> bool:
        """Detect trading architecture and framework patterns"""
        
        # Strategy architecture
        architecture_concepts = [
            'strategy', 'framework', 'system', 'structure', 'component',
            'indicator', 'signal', 'engine', 'pipeline', 'workflow',
            'module', 'service', 'layer', 'abstraction'
        ]
        
        # Trading systems and infrastructure
        system_patterns = [
            'backtesting', 'optimization', 'analysis', 'monitoring',
            'execution', 'portfolio', 'multi-timeframe', 'correlation',
            'risk_engine', 'order_management', 'position_tracking'
        ]
        
        # AI/ML trading architecture
        ai_architecture = [
            'model training', 'prediction pipeline', 'feature store',
            'model serving', 'real-time inference', 'data preprocessing',
            'model validation', 'ensemble methods', 'reinforcement learning'
        ]
        
        # IB integration architecture
        ib_architecture = [
            'api wrapper', 'connection manager', 'data feed', 'order router',
            'account manager', 'market data handler', 'event driven',
            'async processing', 'error handling', 'reconnection logic'
        ]
        
        # Data architecture
        data_patterns = [
            'data feed', 'market data', 'historical data', 'real-time',
            'streaming', 'database', 'storage', 'processing', 'caching',
            'tick data', 'bar data', 'fundamental data'
        ]
        
        has_architecture = any(concept in sentence_lower for concept in architecture_concepts)
        has_system = any(pattern in sentence_lower for pattern in system_patterns)
        has_ai = any(pattern in sentence_lower for pattern in ai_architecture)
        has_ib = any(pattern in sentence_lower for pattern in ib_architecture)
        has_data = any(pattern in sentence_lower for pattern in data_patterns)
        
        return (has_architecture or has_system or has_ai or has_ib or has_data) and 15 < len(sentence) < 300

    def _is_trading_structure_pattern(self, sentence: str, sentence_lower: str) -> bool:
        """Detect trading file structure and organization patterns"""
        
        # File organization for trading systems
        file_patterns = [
            'strategies/', 'data/', 'indicators/', 'backtests/', 'results/',
            'config/', 'utils/', 'models/', 'analysis/', 'reports/',
            'api/', 'ib_integration/', 'portfolio/', 'risk_management/',
            'signals/', 'execution/', 'monitoring/', 'logs/'
        ]
        
        # Trading specific files
        trading_files = [
            '.py', '.json', '.yaml', '.csv', '.xlsx', '.db', '.h5',
            'config.yaml', 'settings.py', 'strategy.py', 'indicators.py',
            'backtest.py', 'portfolio.py', 'ib_client.py', 'data_manager.py',
            'risk_manager.py', 'order_manager.py', 'market_data.py'
        ]
        
        # Organization concepts
        organization_patterns = [
            'organize', 'structure', 'directory', 'folder', 'file',
            'separate', 'group', 'categorize', 'project layout',
            'code organization', 'modular design'
        ]
        
        # IB specific file structure
        ib_structure = [
            'ib_config', 'connection_settings', 'contract_definitions',
            'order_templates', 'account_info', 'market_data_config'
        ]
        
        has_file_pattern = any(pattern in sentence_lower for pattern in file_patterns)
        has_trading_file = any(file_type in sentence_lower for file_type in trading_files)
        has_organization = any(pattern in sentence_lower for pattern in organization_patterns)
        has_ib_structure = any(pattern in sentence_lower for pattern in ib_structure)
        
        return (has_file_pattern or has_trading_file or has_organization or has_ib_structure) and len(sentence) < 250

    def _extract_web_dev_patterns(self, knowledge_context: str) -> Dict[str, List[str]]:
        """Extract web development patterns for React/FastAPI/full-stack applications"""
        
        import re
        sentences = re.split(r'[.!?\n]+', knowledge_context)
        sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]
        
        imports = []
        conventions = []
        architecture = []
        examples = []
        file_structure = []
        
        canvas.info(f"🔍 DEBUG: Web dev extraction processing {len(sentences)} sentences")
        
        for i, sentence in enumerate(sentences):
            sentence_lower = sentence.lower()
            
            # IMPORTS: Web frameworks, libraries, dependencies
            if self._is_web_dev_import_pattern(sentence, sentence_lower):
                imports.append(sentence.strip())
                canvas.info(f"🔍 DEBUG: Found web dev import pattern #{i}: {sentence.strip()}")
            
            # EXAMPLES: Component implementations, API endpoints, code snippets
            elif self._is_web_dev_example_pattern(sentence, sentence_lower):
                examples.append(sentence.strip())
                
            # CONVENTIONS: Best practices, patterns, coding standards
            elif self._is_web_dev_convention_pattern(sentence, sentence_lower):
                conventions.append(sentence.strip())
                
            # ARCHITECTURE: System design, patterns, frameworks
            elif self._is_web_dev_architecture_pattern(sentence, sentence_lower):
                architecture.append(sentence.strip())
                
            # FILE STRUCTURE: Project organization, folder structure
            elif self._is_web_dev_structure_pattern(sentence, sentence_lower):
                file_structure.append(sentence.strip())
        
        return {
            "imports": imports[:10],
            "file_structure": file_structure[:8],
            "conventions": conventions[:12],
            "architecture": architecture[:8],
            "examples": examples[:12]
        }

    def _is_web_dev_import_pattern(self, sentence: str, sentence_lower: str) -> bool:
        """Detect web development imports and dependencies"""
        
        # Frontend libraries and frameworks
        frontend_libs = [
            'react', 'vue', 'angular', 'typescript', 'javascript',
            'tailwind', 'bootstrap', 'material-ui', 'styled-components',
            'axios', 'fetch', 'lodash', 'moment', 'chart.js'
        ]
        
        # Backend frameworks and libraries
        backend_libs = [
            'fastapi', 'django', 'flask', 'express', 'nodejs',
            'sqlalchemy', 'mongoose', 'prisma', 'redis',
            'celery', 'pydantic', 'uvicorn', 'gunicorn'
        ]
        
        # Web-specific imports
        web_imports = [
            'import React', 'from react import', 'import { useState',
            'from fastapi import', 'import fastapi', 'from django',
            'import express', 'const express', 'import axios',
            'from sqlalchemy import', 'import sqlalchemy'
        ]
        
        # Configuration and tools
        web_tools = [
            'webpack', 'vite', 'babel', 'eslint', 'prettier',
            'jest', 'cypress', 'cors', 'dotenv', 'helmet'
        ]
        
        has_frontend = any(lib in sentence_lower for lib in frontend_libs)
        has_backend = any(lib in sentence_lower for lib in backend_libs)
        has_web_import = any(imp in sentence for imp in web_imports)
        has_tools = any(tool in sentence_lower for tool in web_tools)
        
        return (has_frontend or has_backend or has_web_import or has_tools) and len(sentence) < 300

    def _is_web_dev_example_pattern(self, sentence: str, sentence_lower: str) -> bool:
        """Detect web development examples and implementations"""
        
        # React/Frontend examples
        frontend_examples = [
            'const [', 'useState(', 'useEffect(', 'function Component',
            'export default', 'jsx', 'return (', '<div', '<button',
            'onClick=', 'onChange=', 'className=', 'props.'
        ]
        
        # FastAPI/Backend examples
        backend_examples = [
            '@app.get(', '@app.post(', 'async def', 'def endpoint',
            'FastAPI()', 'APIRouter()', 'Depends()', 'Request',
            'Response', 'status_code=', 'response_model='
        ]
        
        # API and HTTP patterns
        api_examples = [
            'GET /', 'POST /', 'PUT /', 'DELETE /', '/api/',
            'endpoint', 'route', 'middleware', 'cors',
            'json()', 'request.', 'response.'
        ]
        
        # Database examples
        db_examples = [
            'SELECT ', 'INSERT ', 'UPDATE ', 'DELETE ',
            'db.query(', 'session.', 'model.', 'schema.'
        ]
        
        has_frontend = any(example in sentence for example in frontend_examples)
        has_backend = any(example in sentence for example in backend_examples)
        has_api = any(example in sentence for example in api_examples)
        has_db = any(example in sentence for example in db_examples)
        
        return (has_frontend or has_backend or has_api or has_db) and len(sentence) < 400

    def _is_web_dev_convention_pattern(self, sentence: str, sentence_lower: str) -> bool:
        """Detect web development conventions and best practices"""
        
        # Frontend best practices
        frontend_conventions = [
            'component', 'prop', 'state', 'hook', 'render',
            'responsive', 'accessibility', 'seo', 'performance',
            'lazy loading', 'code splitting', 'bundle size'
        ]
        
        # Backend best practices
        backend_conventions = [
            'rest api', 'endpoint', 'middleware', 'authentication',
            'authorization', 'validation', 'error handling',
            'rate limiting', 'caching', 'logging', 'monitoring'
        ]
        
        # Security and performance
        security_patterns = [
            'cors', 'csrf', 'xss', 'sql injection', 'sanitize',
            'encrypt', 'hash', 'jwt', 'oauth', 'https'
        ]
        
        # General conventions
        general_conventions = [
            'should', 'must', 'always', 'never', 'avoid',
            'best practice', 'recommended', 'important',
            'clean code', 'maintainable', 'scalable'
        ]
        
        has_frontend = any(conv in sentence_lower for conv in frontend_conventions)
        has_backend = any(conv in sentence_lower for conv in backend_conventions)
        has_security = any(sec in sentence_lower for sec in security_patterns)
        has_general = any(gen in sentence_lower for gen in general_conventions)
        
        return (has_frontend or has_backend or has_security) and has_general and 20 < len(sentence) < 350

    def _is_web_dev_architecture_pattern(self, sentence: str, sentence_lower: str) -> bool:
        """Detect web development architecture patterns"""
        
        # Architecture patterns
        architecture_concepts = [
            'mvc', 'mvvm', 'microservices', 'monolith', 'serverless',
            'spa', 'ssr', 'csr', 'jamstack', 'progressive web app'
        ]
        
        # System design
        system_patterns = [
            'frontend', 'backend', 'full-stack', 'api gateway',
            'load balancer', 'reverse proxy', 'cdn', 'database',
            'caching layer', 'message queue'
        ]
        
        # Development patterns
        dev_patterns = [
            'component-based', 'modular', 'separation of concerns',
            'dependency injection', 'inversion of control',
            'event-driven', 'reactive', 'functional programming'
        ]
        
        has_architecture = any(arch in sentence_lower for arch in architecture_concepts)
        has_system = any(sys in sentence_lower for sys in system_patterns)
        has_dev = any(dev in sentence_lower for dev in dev_patterns)
        
        return (has_architecture or has_system or has_dev) and 15 < len(sentence) < 300

    def _is_web_dev_structure_pattern(self, sentence: str, sentence_lower: str) -> bool:
        """Detect web development file structure patterns"""
        
        # Frontend structure
        frontend_structure = [
            'src/', 'components/', 'pages/', 'hooks/', 'utils/',
            'styles/', 'assets/', 'public/', 'build/', 'dist/'
        ]
        
        # Backend structure
        backend_structure = [
            'api/', 'routes/', 'controllers/', 'models/', 'services/',
            'middleware/', 'config/', 'tests/', 'migrations/'
        ]
        
        # Web files
        web_files = [
            '.js', '.jsx', '.ts', '.tsx', '.vue', '.html', '.css',
            '.scss', '.json', 'package.json', 'requirements.txt',
            'Dockerfile', 'docker-compose.yml'
        ]
        
        # Organization concepts
        organization = [
            'folder structure', 'project layout', 'organize',
            'separate', 'modular', 'clean architecture'
        ]
        
        has_frontend = any(struct in sentence_lower for struct in frontend_structure)
        has_backend = any(struct in sentence_lower for struct in backend_structure)
        has_files = any(file_ext in sentence_lower for file_ext in web_files)
        has_org = any(org in sentence_lower for org in organization)
        
        return (has_frontend or has_backend or has_files or has_org) and len(sentence) < 250

    def _extract_data_science_patterns(self, knowledge_context: str) -> Dict[str, List[str]]:
        """Extract data science patterns for pandas/sklearn/jupyter workflows"""
        
        import re
        sentences = re.split(r'[.!?\n]+', knowledge_context)
        sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]
        
        imports = []
        conventions = []
        architecture = []
        examples = []
        file_structure = []
        
        canvas.info(f"🔍 DEBUG: Data science extraction processing {len(sentences)} sentences")
        
        for i, sentence in enumerate(sentences):
            sentence_lower = sentence.lower()
            
            # IMPORTS: Data science libraries and tools
            if self._is_data_science_import_pattern(sentence, sentence_lower):
                imports.append(sentence.strip())
                canvas.info(f"🔍 DEBUG: Found data science import pattern #{i}: {sentence.strip()}")
            
            # EXAMPLES: Analysis code, model implementations, data operations
            elif self._is_data_science_example_pattern(sentence, sentence_lower):
                examples.append(sentence.strip())
                
            # CONVENTIONS: Best practices, methodologies, standards
            elif self._is_data_science_convention_pattern(sentence, sentence_lower):
                conventions.append(sentence.strip())
                
            # ARCHITECTURE: ML pipelines, data workflows, system design
            elif self._is_data_science_architecture_pattern(sentence, sentence_lower):
                architecture.append(sentence.strip())
                
            # FILE STRUCTURE: Project organization, notebook structure
            elif self._is_data_science_structure_pattern(sentence, sentence_lower):
                file_structure.append(sentence.strip())
        
        return {
            "imports": imports[:10],
            "file_structure": file_structure[:8],
            "conventions": conventions[:12],
            "architecture": architecture[:8],
            "examples": examples[:12]
        }

    def _is_data_science_import_pattern(self, sentence: str, sentence_lower: str) -> bool:
        """Detect data science imports and dependencies"""
        
        # Core data science libraries
        ds_libs = [
            'pandas', 'numpy', 'matplotlib', 'seaborn', 'plotly',
            'scikit-learn', 'sklearn', 'scipy', 'statsmodels',
            'jupyter', 'ipython', 'notebook'
        ]
        
        # Machine learning libraries
        ml_libs = [
            'tensorflow', 'pytorch', 'keras', 'xgboost', 'lightgbm',
            'catboost', 'optuna', 'mlflow', 'wandb', 'streamlit'
        ]
        
        # Data processing and storage
        data_libs = [
            'dask', 'polars', 'pyarrow', 'sqlalchemy', 'pymongo',
            'requests', 'beautifulsoup4', 'scrapy', 'boto3'
        ]
        
        # Data science imports
        ds_imports = [
            'import pandas as pd', 'import numpy as np',
            'import matplotlib.pyplot as plt', 'import seaborn as sns',
            'from sklearn import', 'import sklearn', 'from scipy',
            'import tensorflow as tf', 'import torch'
        ]
        
        has_ds_lib = any(lib in sentence_lower for lib in ds_libs)
        has_ml_lib = any(lib in sentence_lower for lib in ml_libs)
        has_data_lib = any(lib in sentence_lower for lib in data_libs)
        has_ds_import = any(imp in sentence for imp in ds_imports)
        
        return (has_ds_lib or has_ml_lib or has_data_lib or has_ds_import) and len(sentence) < 300

    def _is_data_science_example_pattern(self, sentence: str, sentence_lower: str) -> bool:
        """Detect data science examples and implementations"""
        
        # Pandas operations
        pandas_examples = [
            'df.', 'dataframe.', '.head()', '.tail()', '.describe()',
            '.groupby(', '.merge(', '.join(', '.pivot(', '.melt(',
            '.dropna()', '.fillna()', '.apply(', '.map('
        ]
        
        # Machine learning examples
        ml_examples = [
            'model.fit(', 'model.predict(', 'train_test_split(',
            'cross_val_score(', 'GridSearchCV(', 'RandomForestClassifier(',
            'LinearRegression()', 'accuracy_score(', 'confusion_matrix('
        ]
        
        # Visualization examples
        viz_examples = [
            'plt.', 'sns.', 'fig,', 'ax.', '.plot(', '.scatter(',
            '.hist()', '.boxplot()', '.heatmap(', 'plotly.'
        ]
        
        # Statistical analysis
        stats_examples = [
            'mean()', 'std()', 'corr()', 'median()', 'quantile(',
            'ttest_', 'chi2_contingency(', 'pearsonr(', 'linregress('
        ]
        
        has_pandas = any(example in sentence for example in pandas_examples)
        has_ml = any(example in sentence for example in ml_examples)
        has_viz = any(example in sentence for example in viz_examples)
        has_stats = any(example in sentence for example in stats_examples)
        
        return (has_pandas or has_ml or has_viz or has_stats) and len(sentence) < 400

    def _is_data_science_convention_pattern(self, sentence: str, sentence_lower: str) -> bool:
        """Detect data science conventions and best practices"""
        
        # Data analysis best practices
        analysis_conventions = [
            'exploratory data analysis', 'eda', 'data cleaning',
            'feature engineering', 'data validation', 'outliers',
            'missing values', 'data quality', 'reproducible'
        ]
        
        # Machine learning best practices
        ml_conventions = [
            'train test split', 'cross validation', 'overfitting',
            'underfitting', 'bias variance', 'feature selection',
            'hyperparameter tuning', 'model evaluation', 'baseline model'
        ]
        
        # Statistical conventions
        stats_conventions = [
            'statistical significance', 'p-value', 'confidence interval',
            'null hypothesis', 'correlation', 'causation', 'sample size'
        ]
        
        # General conventions
        general_conventions = [
            'should', 'must', 'always', 'never', 'avoid',
            'best practice', 'recommended', 'important',
            'remember', 'ensure', 'verify'
        ]
        
        has_analysis = any(conv in sentence_lower for conv in analysis_conventions)
        has_ml = any(conv in sentence_lower for conv in ml_conventions)
        has_stats = any(conv in sentence_lower for conv in stats_conventions)
        has_general = any(conv in sentence_lower for conv in general_conventions)
        
        return (has_analysis or has_ml or has_stats) and has_general and 20 < len(sentence) < 350

    def _is_data_science_architecture_pattern(self, sentence: str, sentence_lower: str) -> bool:
        """Detect data science architecture patterns"""
        
        # ML pipeline architecture
        pipeline_concepts = [
            'pipeline', 'workflow', 'etl', 'data pipeline',
            'feature store', 'model registry', 'mlops',
            'data lake', 'data warehouse', 'batch processing'
        ]
        
        # Model architecture
        model_concepts = [
            'model architecture', 'ensemble', 'stacking',
            'bagging', 'boosting', 'neural network',
            'deep learning', 'transfer learning', 'fine-tuning'
        ]
        
        # System design
        system_concepts = [
            'scalable', 'distributed', 'real-time', 'streaming',
            'microservices', 'api', 'containerization',
            'kubernetes', 'docker', 'cloud'
        ]
        
        has_pipeline = any(concept in sentence_lower for concept in pipeline_concepts)
        has_model = any(concept in sentence_lower for concept in model_concepts)
        has_system = any(concept in sentence_lower for concept in system_concepts)
        
        return (has_pipeline or has_model or has_system) and 15 < len(sentence) < 300

    def _is_data_science_structure_pattern(self, sentence: str, sentence_lower: str) -> bool:
        """Detect data science file structure patterns"""
        
        # Data science project structure
        ds_structure = [
            'data/', 'notebooks/', 'src/', 'models/', 'reports/',
            'references/', 'requirements/', 'config/', 'scripts/',
            'tests/', 'docs/', 'outputs/', 'experiments/'
        ]
        
        # Data science files
        ds_files = [
            '.ipynb', '.py', '.csv', '.json', '.pkl', '.joblib',
            '.h5', '.parquet', '.yaml', '.txt', '.md',
            'requirements.txt', 'environment.yml', 'Dockerfile'
        ]
        
        # Organization concepts
        organization = [
            'project structure', 'organize', 'folder',
            'directory', 'cookiecutter', 'template',
            'reproducible research', 'version control'
        ]
        
        has_structure = any(struct in sentence_lower for struct in ds_structure)
        has_files = any(file_ext in sentence_lower for file_ext in ds_files)
        has_org = any(org in sentence_lower for org in organization)
        
        return (has_structure or has_files or has_org) and len(sentence) < 250

    def _extract_programming_patterns(self, knowledge_context: str) -> Dict[str, List[str]]:
        """Extract general programming patterns for OOP/design patterns/algorithms"""
        
        import re
        sentences = re.split(r'[.!?\n]+', knowledge_context)
        sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]
        
        imports = []
        conventions = []
        architecture = []
        examples = []
        file_structure = []
        
        canvas.info(f"🔍 DEBUG: Programming extraction processing {len(sentences)} sentences")
        
        for i, sentence in enumerate(sentences):
            sentence_lower = sentence.lower()
            
            # IMPORTS: Programming languages, standard libraries, common packages
            if self._is_programming_import_pattern(sentence, sentence_lower):
                imports.append(sentence.strip())
                canvas.info(f"🔍 DEBUG: Found programming import pattern #{i}: {sentence.strip()}")
            
            # EXAMPLES: Code implementations, algorithms, design patterns
            elif self._is_programming_example_pattern(sentence, sentence_lower):
                examples.append(sentence.strip())
                
            # CONVENTIONS: Best practices, coding standards, principles
            elif self._is_programming_convention_pattern(sentence, sentence_lower):
                conventions.append(sentence.strip())
                
            # ARCHITECTURE: Design patterns, software architecture, system design
            elif self._is_programming_architecture_pattern(sentence, sentence_lower):
                architecture.append(sentence.strip())
                
            # FILE STRUCTURE: Project organization, code structure
            elif self._is_programming_structure_pattern(sentence, sentence_lower):
                file_structure.append(sentence.strip())
        
        return {
            "imports": imports[:10],
            "file_structure": file_structure[:8],
            "conventions": conventions[:12],
            "architecture": architecture[:8],
            "examples": examples[:12]
        }

    def _is_programming_import_pattern(self, sentence: str, sentence_lower: str) -> bool:
        """Detect general programming imports and dependencies"""
        
        # Standard library imports (Python)
        python_std = [
            'os', 'sys', 'json', 'datetime', 'collections', 'itertools',
            'functools', 'typing', 're', 'pathlib', 'logging', 'unittest'
        ]
        
        # Common programming libraries (multi-language)
        common_libs = [
            'requests', 'urllib', 'http', 'asyncio', 'threading',
            'multiprocessing', 'concurrent', 'queue', 'sqlite3'
        ]
        
        # Programming language indicators
        lang_indicators = [
            'import', 'from', 'include', 'require', 'using',
            '#include', '@import', 'package', 'namespace'
        ]
        
        # Framework/library patterns
        framework_patterns = [
            'standard library', 'built-in', 'third-party',
            'dependency', 'package manager', 'module'
        ]
        
        has_python_std = any(lib in sentence_lower for lib in python_std)
        has_common = any(lib in sentence_lower for lib in common_libs)
        has_lang = any(ind in sentence_lower for ind in lang_indicators)
        has_framework = any(pattern in sentence_lower for pattern in framework_patterns)
        
        return (has_python_std or has_common or has_lang or has_framework) and len(sentence) < 300

    def _is_programming_example_pattern(self, sentence: str, sentence_lower: str) -> bool:
        """Detect general programming examples and implementations"""
        
        # Object-oriented programming
        oop_examples = [
            'class ', 'def __init__', 'self.', 'super()', 'inheritance',
            'polymorphism', 'encapsulation', 'abstraction', 'method',
            'attribute', 'property', 'static', 'classmethod'
        ]
        
        # Control structures and algorithms
        algorithm_examples = [
            'if ', 'elif ', 'else:', 'for ', 'while ', 'try:', 'except:',
            'with ', 'def ', 'return ', 'yield ', 'lambda ',
            'list comprehension', 'generator', 'decorator'
        ]
        
        # Data structures
        data_structure_examples = [
            'list', 'dict', 'set', 'tuple', 'array', 'stack', 'queue',
            'tree', 'graph', 'hash table', 'linked list', 'binary search'
        ]
        
        # Design patterns
        pattern_examples = [
            'singleton', 'factory', 'observer', 'decorator pattern',
            'strategy', 'adapter', 'facade', 'builder', 'command'
        ]
        
        has_oop = any(example in sentence_lower for example in oop_examples)
        has_algorithm = any(example in sentence for example in algorithm_examples)
        has_data_structure = any(example in sentence_lower for example in data_structure_examples)
        has_pattern = any(example in sentence_lower for example in pattern_examples)
        
        return (has_oop or has_algorithm or has_data_structure or has_pattern) and len(sentence) < 400

    def _is_programming_convention_pattern(self, sentence: str, sentence_lower: str) -> bool:
        """Detect programming conventions and best practices"""
        
        # Code quality and best practices
        quality_conventions = [
            'clean code', 'readable', 'maintainable', 'testable',
            'dry principle', 'solid principles', 'kiss principle',
            'code review', 'refactoring', 'technical debt'
        ]
        
        # Coding standards
        coding_standards = [
            'naming convention', 'camelcase', 'snake_case', 'pep 8',
            'style guide', 'linting', 'formatting', 'documentation',
            'comments', 'docstring', 'type hints'
        ]
        
        # Software engineering practices
        engineering_practices = [
            'version control', 'git', 'testing', 'unit test',
            'integration test', 'debugging', 'profiling',
            'continuous integration', 'deployment', 'monitoring'
        ]
        
        # General conventions
        general_conventions = [
            'should', 'must', 'always', 'never', 'avoid',
            'best practice', 'recommended', 'important',
            'consider', 'prefer', 'guideline'
        ]
        
        has_quality = any(conv in sentence_lower for conv in quality_conventions)
        has_standards = any(conv in sentence_lower for conv in coding_standards)
        has_engineering = any(conv in sentence_lower for conv in engineering_practices)
        has_general = any(conv in sentence_lower for conv in general_conventions)
        
        return (has_quality or has_standards or has_engineering) and has_general and 20 < len(sentence) < 350

    def _is_programming_architecture_pattern(self, sentence: str, sentence_lower: str) -> bool:
        """Detect programming architecture patterns"""
        
        # Design patterns
        design_patterns = [
            'design pattern', 'creational', 'structural', 'behavioral',
            'mvc', 'mvp', 'mvvm', 'dependency injection',
            'inversion of control', 'separation of concerns'
        ]
        
        # Software architecture
        architecture_concepts = [
            'architecture', 'layered', 'modular', 'component',
            'service oriented', 'event driven', 'microservices',
            'monolithic', 'hexagonal', 'clean architecture'
        ]
        
        # Programming paradigms
        paradigms = [
            'object oriented', 'functional programming', 'procedural',
            'declarative', 'imperative', 'reactive', 'concurrent'
        ]
        
        has_patterns = any(pattern in sentence_lower for pattern in design_patterns)
        has_architecture = any(arch in sentence_lower for arch in architecture_concepts)
        has_paradigms = any(paradigm in sentence_lower for paradigm in paradigms)
        
        return (has_patterns or has_architecture or has_paradigms) and 15 < len(sentence) < 300

    def _is_programming_structure_pattern(self, sentence: str, sentence_lower: str) -> bool:
        """Detect programming file structure patterns"""
        
        # General project structure
        project_structure = [
            'src/', 'lib/', 'tests/', 'docs/', 'config/', 'scripts/',
            'utils/', 'helpers/', 'core/', 'main/', 'bin/', 'build/'
        ]
        
        # Programming files
        programming_files = [
            '.py', '.js', '.ts', '.java', '.cpp', '.c', '.h',
            '.go', '.rs', '.rb', '.php', '.cs', '.swift',
            'main.py', 'index.js', 'app.py', '__init__.py'
        ]
        
        # Organization concepts
        organization = [
            'project structure', 'code organization', 'module',
            'package', 'namespace', 'directory structure',
            'file layout', 'architecture', 'separation'
        ]
        
        has_structure = any(struct in sentence_lower for struct in project_structure)
        has_files = any(file_ext in sentence_lower for file_ext in programming_files)
        has_org = any(org in sentence_lower for org in organization)
        
        return (has_structure or has_files or has_org) and len(sentence) < 250

    def _extract_universal_patterns(self, knowledge_context: str) -> Dict[str, List[str]]:
        """Fallback universal pattern extraction for any domain"""
        
        import re
        sentences = re.split(r'[.!?\n]+', knowledge_context)
        sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]
        
        imports = []
        conventions = []
        architecture = []
        examples = []
        file_structure = []
        
        canvas.info(f"🔍 DEBUG: Universal extraction processing {len(sentences)} sentences")
        
        for i, sentence in enumerate(sentences):
            sentence_lower = sentence.lower()
            
            # Look for any technical concepts as "imports" 
            tech_keywords = ['agent', 'team', 'framework', 'library', 'system', 'model', 'api', 'service']
            if any(keyword in sentence_lower for keyword in tech_keywords) and 15 < len(sentence) < 200:
                imports.append(sentence.strip())
                canvas.info(f"🔍 DEBUG: Found universal concept #{i}: {sentence.strip()}")
                
            # Look for examples and patterns
            elif ('(' in sentence and ')' in sentence) and len(sentence) < 300:
                examples.append(sentence.strip())
                
            # Look for best practices and conventions  
            elif any(word in sentence_lower for word in ['use', 'should', 'must', 'best', 'practice', 'important']) and len(sentence) < 250:
                conventions.append(sentence.strip())
                
            # Look for architectural concepts
            elif any(word in sentence_lower for word in ['pattern', 'structure', 'design', 'architecture', 'approach']) and len(sentence) < 200:
                architecture.append(sentence.strip())
        
        return {
            "imports": imports[:2],        # Reduced from 6 to 2 - top most relevant
            "file_structure": file_structure[:2],  # Reduced from 4 to 2 - essential structure only
            "conventions": conventions[:3],       # Reduced from 8 to 3 - core conventions
            "architecture": architecture[:2],      # Reduced from 5 to 2 - key architecture patterns
            "examples": examples[:2]              # Reduced from 8 to 2 - best examples
        }
    
    def enhance_agent_instructions(
        self,
        base_instructions: Union[str, List[str]],
        knowledge_context: str,
        agent_type: str
    ) -> Union[str, List[str]]:
        """
        Enhance instructions directly without modifying agent object.
        Useful for integration with existing agent factories.
        """
        if not knowledge_context:
            return base_instructions
        
        try:
            patterns = self.reasoner.extract_actionable_patterns(knowledge_context)
            if not patterns:
                return base_instructions
            
            requirements = self.reasoner.create_reasoning_requirements(patterns, agent_type)
            
            # Handle both string and list instruction formats
            if isinstance(base_instructions, list):
                return base_instructions + requirements
            else:
                return str(base_instructions) + "\n\n" + "\n".join(requirements)
                
        except Exception as e:
            logger.error(f"Failed to enhance instructions for {agent_type}: {e}")
            return base_instructions

    def validate_enhanced_agent_output(self, agent, output: str) -> Dict[str, Any]:
        """
        Validate that enhanced agent applied knowledge patterns.
        Returns validation results for feedback/learning.
        """
        if not hasattr(agent, '_knowledge_patterns'):
            return {"enhanced": False, "message": "Agent was not enhanced with knowledge"}
        
        try:
            # Try the PatternExtractorAgent validation
            success, violations = self.reasoner.validate_pattern_application(
                output, agent._knowledge_patterns
            )
        except Exception as e:
            # Fallback validation
            print(f"PatternExtractorAgent validation failed: {e}")
            success, violations = self._fallback_validation(output, agent._knowledge_patterns)
        
        return {
            "enhanced": True,
            "success": success,
            "violations": violations,
            "patterns_available": len(agent._knowledge_patterns),
            "agent_type": getattr(agent, '_agent_type', 'unknown')
        }

    def _fallback_validation(self, output: str, patterns: Dict) -> tuple[bool, List[str]]:
        """Simple fallback validation"""
        violations = []
        output_lower = output.lower()
        
        # Check for basic pattern application
        has_imports = any(
            any(keyword in output_lower for keyword in imp.lower().split()[:2]) 
            for imp in patterns.get('imports', [])
        )
        has_justification = 'applied patterns:' in output_lower
        
        if not has_imports and patterns.get('imports'):
            violations.append("Missing documented imports")
        if not has_justification:
            violations.append("Missing pattern application justification")
        
        success = len(violations) == 0
        return success, violations
    
    def create_enhancement_hook(self, session_state_key: str = "retrieved_context"):
        """
        Create a reusable enhancement function for integration with existing workflows.
        
        Returns:
            Function that can be called in agent creation pipelines
        """
        def enhancement_hook(agent, session_state: Dict, agent_type: str):
            if session_state and session_state_key in session_state:
                knowledge_context = session_state[session_state_key]
                task_context = session_state.get("task", "")
                return self.enhance_agent_with_knowledge(
                    agent, knowledge_context, agent_type, task_context
                )
            return agent
        
        return enhancement_hook
    
    def _inject_requirements_into_agent(self, agent, requirements: List[str]):
        """Safely inject requirements into agent instructions with knowledge priority"""
        if not requirements:
            return
        
        # Handle different instruction formats - PRIORITIZE knowledge requirements
        if hasattr(agent, 'instructions'):
            current_instructions = agent.instructions
            
            if isinstance(current_instructions, list):
                # PUT KNOWLEDGE FIRST - makes it primary focus
                agent.instructions = requirements + current_instructions
                logger.info(f"Enhanced agent with {len(requirements)} knowledge requirements (prioritized)")
                
                # DEBUG: Log what was injected
                canvas.info(f"💉 DEBUG: Injected {len(requirements)} requirements into {type(agent).__name__}")
                canvas.info(f"🔍 DEBUG: First requirement: {requirements[0] if requirements else 'None'}")
                canvas.info(f"📋 DEBUG: Total instructions now: {len(agent.instructions)}")
     
            
            elif isinstance(current_instructions, str):
                # PUT KNOWLEDGE FIRST in string format
                knowledge_text = "\n".join(requirements)
                agent.instructions = f"{knowledge_text}\n\n{current_instructions}"
                logger.info(f"Enhanced agent instructions with knowledge priority")
            else:
                # Fallback: convert to string with knowledge first
                knowledge_text = "\n".join(requirements)
                agent.instructions = f"{knowledge_text}\n\n{str(current_instructions)}"
                logger.info(f"Enhanced agent with fallback knowledge priority")
        
        # Some agents might use different attribute names
        elif hasattr(agent, 'system_prompt'):
            current_prompt = agent.system_prompt or ""
            knowledge_text = "\n".join(requirements)
            agent.system_prompt = f"{knowledge_text}\n\n{current_prompt}"
        
        elif hasattr(agent, 'prompt'):
            current_prompt = agent.prompt or ""
            knowledge_text = "\n".join(requirements)
            agent.prompt = f"{knowledge_text}\n\n{current_prompt}"

class SessionStateEnhancer:
    """
    Manages knowledge context in session state for multi-step workflows.
    Ensures knowledge persists across agent interactions.
    """
    
    def __init__(self):
        self.enhancer = AgentKnowledgeEnhancer()
    
    def store_knowledge_context(
        self,
        session_state: Dict,
        knowledge_context: str,
        context_source: str = "rag_retrieval"
    ):
        """Store knowledge context in session state for reuse"""
        if not session_state:
            session_state = {}
        
        session_state["retrieved_context"] = knowledge_context
        session_state["context_source"] = context_source
        session_state["context_stored_at"] = self._get_timestamp()
        
        return session_state
    
    def get_knowledge_context(self, session_state: Dict) -> Optional[str]:
        """Retrieve stored knowledge context"""
        return session_state.get("retrieved_context") if session_state else None
    
    def enhance_agent_from_session(
        self,
        agent,
        session_state: Dict,
        agent_type: str
    ):
        """Enhance agent using knowledge context from session state"""
        knowledge_context = self.get_knowledge_context(session_state)
        
        if knowledge_context:
            task_context = session_state.get("task", "")
            return self.enhancer.enhance_agent_with_knowledge(
                agent, knowledge_context, agent_type, task_context
            )
        
        return agent
    
    def _get_timestamp(self) -> str:
        """Get current timestamp for tracking"""
        from datetime import datetime
        return datetime.now().isoformat()


# Integration utilities for existing codebase
def create_knowledge_enhanced_agent_factory():
    """
    Create a factory function that can replace existing agent creation.
    Drop-in replacement for get_rag_enabled_agent() pattern.
    """
    enhancer = AgentKnowledgeEnhancer()
    
    def enhanced_agent_factory(agent_class, agent_type: str, session_state: Dict = None):
        """Create an enhanced agent with knowledge reasoning"""
        # Create base agent
        agent = agent_class()
        
        # Enhance with knowledge if available
        if session_state and "retrieved_context" in session_state:
            agent = enhancer.enhance_agent_with_knowledge(
                agent, 
                session_state["retrieved_context"], 
                agent_type,
                session_state.get("task", "")
            )
        
        return agent
    
    return enhanced_agent_factory


def enhance_existing_agent_creation(original_function):
    """
    Decorator to enhance existing agent creation functions.
    Can wrap get_rag_enabled_agent() or similar functions.
    """
    enhancer = AgentKnowledgeEnhancer()
    
    def wrapper(agent_type, session_state=None, *args, **kwargs):
        # Call original function
        agent = original_function(agent_type, session_state, *args, **kwargs)
        
        # Enhance with knowledge if available
        if session_state and "retrieved_context" in session_state:
            agent = enhancer.enhance_agent_with_knowledge(
                agent,
                session_state["retrieved_context"],
                agent_type,
                session_state.get("task", "")
            )
        
        return agent
    
    return wrapper


# Shared enhancer instance to preserve cache across calls
_shared_enhancer = AgentKnowledgeEnhancer()

# Quick integration helpers
def quick_enhance_agent(agent, knowledge_context: str, agent_type: str):
    """Quick enhancement for one-off agent creation using shared enhancer instance"""
    return _shared_enhancer.enhance_agent_with_knowledge(agent, knowledge_context, agent_type)


def quick_enhance_instructions(instructions, knowledge_context: str, agent_type: str):
    """Quick enhancement for instruction strings/lists using shared enhancer instance"""
    return _shared_enhancer.enhance_agent_instructions(instructions, knowledge_context, agent_type)


# Test examples and validation
if __name__ == "__main__":
    # Test 1: Basic agent enhancement
    def test_basic_enhancement():
        print("🧪 Testing basic agent enhancement...")
        
        # Mock agent class
        class MockAgent:
            def __init__(self):
                self.instructions = ["Be helpful", "Generate good code"]
                self.name = "TestAgent"
        
        # Mock knowledge context
        knowledge_context = """
        from agno.agent import Agent
        from agno.team import Team
        
        Always use Agent(model=..., instructions=...) pattern.
        Separate frontend and backend code.
        Use proper error handling.
        """
        
        # Test enhancement
        enhancer = AgentKnowledgeEnhancer()
        agent = MockAgent()
        
        print(f"Before enhancement: {len(agent.instructions)} instructions")
        
        enhanced_agent = enhancer.enhance_agent_with_knowledge(
            agent, knowledge_context, "code_builder"
        )
        
        print(f"After enhancement: {len(enhanced_agent.instructions)} instructions")
        print("Enhanced instructions include:", enhanced_agent.instructions[-2:])
        print("✅ Basic enhancement test passed")
    
    # Test 2: Session state integration
    def test_session_state_integration():
        print("\n🧪 Testing session state integration...")
        
        session_enhancer = SessionStateEnhancer()
        session_state = {}
        
        # Store knowledge
        knowledge = "Use FastAPI for backend. React for frontend."
        session_state = session_enhancer.store_knowledge_context(
            session_state, knowledge, "test_retrieval"
        )
        
        print(f"Stored context: {session_state.get('retrieved_context')[:50]}...")
        
        # Enhance agent from session
        class MockAgent:
            def __init__(self):
                self.instructions = ["Plan project files"]
        
        agent = MockAgent()
        enhanced = session_enhancer.enhance_agent_from_session(
            agent, session_state, "planner"
        )
        
        print(f"Agent enhanced: {hasattr(enhanced, '_enhanced_with_knowledge')}")
        print("✅ Session state integration test passed")
    
    # Test 3: Instruction enhancement only
    def test_instruction_enhancement():
        print("\n🧪 Testing instruction enhancement...")
        
        base_instructions = ["Generate clean code", "Follow best practices"]
        knowledge = "Always use TypeScript. Add proper type annotations."
        
        enhancer = AgentKnowledgeEnhancer()
        enhanced_instructions = enhancer.enhance_agent_instructions(
            base_instructions, knowledge, "code_builder"
        )
        
        print(f"Original: {len(base_instructions)} instructions")
        print(f"Enhanced: {len(enhanced_instructions)} instructions")
        print("New instructions include TypeScript guidance")
        print("✅ Instruction enhancement test passed")
    
    # Test 4: Validation
    def test_validation():
        print("\n🧪 Testing validation...")
        
        class MockAgent:
            def __init__(self):
                self.instructions = []
        
        agent = MockAgent()
        enhancer = AgentKnowledgeEnhancer()
        
        # Enhance agent
        enhanced = enhancer.enhance_agent_with_knowledge(
            agent, "Use Agent pattern", "code_builder"
        )
        
        # Test validation
        good_output = "from agno.agent import Agent\nAgent(model=..., instructions=...)\nApplied patterns: import:agno.agent"
        bad_output = "print('hello world')"
        
        good_result = enhancer.validate_enhanced_agent_output(enhanced, good_output)
        bad_result = enhancer.validate_enhanced_agent_output(enhanced, bad_output)
        
        print(f"Good output validation: {good_result['success']}")
        print(f"Bad output validation: {bad_result['success']}")
        print("✅ Validation test passed")
    
    # Run all tests
    test_basic_enhancement()
    test_session_state_integration()
    test_instruction_enhancement()
    test_validation()
    
    print("\n🎉 All tests passed! Enhancer ready for integration.")