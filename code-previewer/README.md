# Code Previewer

A fully functional **code previewer web application** with Docker containerization.

Upload any code file from your browser and instantly view it with beautiful syntax highlighting powered by `react-syntax-highlighter`.

## Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + react-syntax-highlighter |
| Backend | Node.js 18 + Express + multer |
| Containerization | Docker + Docker Compose |

## Supported File Types

`.js` · `.jsx` · `.ts` · `.tsx` · `.py` · `.java` · `.cpp` · `.c` · `.txt`

## Project Structure

```
code-previewer/
├── backend/
│   ├── server.js          # Express API (port 4000)
│   ├── package.json
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.js         # Main React component
│   │   └── index.js
│   ├── public/
│   │   └── index.html
│   ├── package.json
│   └── Dockerfile
└── docker-compose.yml
```

## How to Run

### Using Docker Compose (recommended)

```bash
cd code-previewer
docker-compose up --build
```

Then open your browser at **http://localhost:3000**.

### Without Docker

**Backend:**
```bash
cd code-previewer/backend
npm install
node server.js
```

**Frontend** (in a separate terminal):
```bash
cd code-previewer/frontend
npm install
npm start
```

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/upload` | Upload a code file. Returns `{ filename, content }` |

## Features

- 📁 Upload any code file via the browser
- 🎨 Syntax highlighting with the `atomDark` theme
- 🔢 Line numbers displayed alongside code
- 🌐 Language auto-detection based on file extension
- 🐳 Fully containerised with Docker Compose
