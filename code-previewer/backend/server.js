const express = require('express');
const multer = require('multer');
const cors = require('cors');
const fs = require('fs');
const path = require('path');

const app = express();
const upload = multer({
  dest: 'uploads/',
  limits: { fileSize: 1 * 1024 * 1024 }, // 1 MB max
});

app.use(cors());

app.post('/upload', upload.single('codefile'), async (req, res) => {
  if (!req.file) return res.status(400).json({ error: 'No file uploaded.' });

  const filePath = path.join(__dirname, req.file.path);
  try {
    const fileContent = await fs.promises.readFile(filePath, 'utf-8');
    res.json({
      filename: req.file.originalname,
      content: fileContent,
    });
  } finally {
    fs.promises.unlink(filePath).catch(() => {});
  }
});

const PORT = 4000;
app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
