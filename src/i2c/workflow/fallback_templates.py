# src/i2c/workflow/fallback_templates.py
TEMPLATES_BY_LANG = {
    "python": (
        "from fastapi import FastAPI\n\n"
        "app = FastAPI()\n\n"
        "if __name__ == '__main__':\n"
        "    import uvicorn\n"
        "    uvicorn.run(app, host='0.0.0.0', port=8000)\n"
    ),
    "jsx": (
        'import React from "react";\n\n'
        "function App() {\n"
        "  return (\n"
        '    <div className=\"App\">\n'
        "      {/* TODO: Render snippets here */}\n"
        "    </div>\n"
        "  );\n"
        "}\n\nexport default App;\n"
    ),
    # ↓ easily extend for new langs
    "tsx": "import React from 'react';\nexport const App: React.FC = () => <div />;\n",
    "go":  "package main\n\nimport \"net/http\"\n\nfunc main() { _ = http.ListenAndServe(\":8080\", nil) }\n",
}
