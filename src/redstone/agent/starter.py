"""Small, trusted starting files for an explicitly selected React/Vite project.

Creation writes these through the workspace's normal quota and path checks.
Dependencies are never installed on the host or during project creation;
RuntimeManager installs them inside its restricted sandbox when preview starts.
"""

from __future__ import annotations

import json

from ..config import Limits
from ..workspace.files import write_file
from ..workspace.manager import Workspace

_PACKAGE = {
    "name": "redstone-starter",
    "version": "1.0.0",
    "private": True,
    "type": "module",
    "scripts": {"dev": "vite", "build": "tsc --noEmit && vite build"},
    "dependencies": {"react": "19.1.0", "react-dom": "19.1.0"},
    "devDependencies": {
        "@types/react": "19.1.0",
        "@types/react-dom": "19.1.0",
        "typescript": "5.8.3",
        "vite": "7.3.5",
    },
}

_TSCONFIG = {
    "compilerOptions": {
        "target": "ES2020",
        "lib": ["ES2020", "DOM", "DOM.Iterable"],
        "module": "ESNext",
        "moduleResolution": "Bundler",
        "jsx": "react-jsx",
        "strict": True,
        "skipLibCheck": True,
        "noEmit": True,
        "types": ["vite/client"],
    },
    "include": ["src"],
}

_FILES = (
    ("package.json", json.dumps(_PACKAGE, indent=2) + "\n"),
    ("tsconfig.json", json.dumps(_TSCONFIG, indent=2) + "\n"),
    ("index.html", "<!doctype html>\n<html lang=\"en\">\n<head>\n"
     "  <meta charset=\"UTF-8\" />\n"
     "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />\n"
     "  <title>Redstone project</title>\n</head>\n<body>\n"
     "  <div id=\"root\"></div>\n"
     "  <script type=\"module\" src=\"/src/main.tsx\"></script>\n"
     "</body>\n</html>\n"),
    ("src/main.tsx", "import { createRoot } from 'react-dom/client'\n"
     "import './style.css'\n\n"
     "function App() {\n"
     "  return <main><h1>Ready to build</h1><p>Tell Redstone what to make.</p></main>\n"
     "}\n\n"
     "createRoot(document.getElementById('root')!).render(<App />)\n"),
    ("src/style.css", "body { margin: 0; background: #f6f2ea; color: #18232b; "
     "font: 18px system-ui, sans-serif; }\n"
     "main { max-width: 48rem; margin: 15vh auto; padding: 2rem; }\n"),
)


def create_react_starter(workspace: Workspace, limits: Limits) -> None:
    """Seed only a new, empty workspace; never install or run project code."""
    for path, content in _FILES:
        write_file(workspace.project_root, path, content, limits)
