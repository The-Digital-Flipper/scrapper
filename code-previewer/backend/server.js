const express = require('express');
const multer = require('multer');
const cors = require('cors');
const fs = require('fs');
const path = require('path');

const app = express();
const upload = multer({ dest: 'uploads/' });

app.use(cors());
app.use(express.static('uploads'));

app.post('/upload', upload.single('codefile'), (req, res) => {
  if (!req.file) return res.status(400).json({ error: 'No file uploaded.' });

  const filePath = path.join(__dirname, req.file.path);
  const fileContent = fs.readFileSync(filePath, 'utf-8');

  res.json({
    filename: req.file.originalname,
    content: fileContent,
  });
});

const PORT = 4000;
app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
