import express from "express";
import path from "path";
import { fileURLToPath } from "url";

const app = express();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
 const PORT = 3000;

// publicフォルダを公開
app.use(express.static("public"));

// トップページ
app.get("/", (req, res) => {
    res.sendFile(path.join(__dirname, "views", "index.html"));
});

app.get("/test", (req, res) => {
    res.sendFile(path.join(__dirname, "views", "test.html"));
});

app.listen(PORT, () => {
    console.log(`Server Start`);
    console.log(`http://localhost:${PORT}`);
});
