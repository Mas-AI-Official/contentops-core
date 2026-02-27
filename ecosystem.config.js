module.exports = {
    apps: [
        {
            name: "contentops-backend",
            script: "venv/Scripts/python.exe",
            args: "-m uvicorn app.main:app --host 0.0.0.0 --port 8100",
            cwd: "backend",
            interpreter: "none",
            env: {
                NODE_ENV: "production",
            }
        },
        {
            name: "contentops-autonomous-worker",
            script: "auto_loop.js",
            cwd: "./",
            env: {
                NODE_ENV: "production",
            }
        },
        {
            name: "contentops-frontend",
            script: "npm",
            args: "run dev",
            cwd: "frontend",
            env: {
                NODE_ENV: "development",
            }
        }
    ]
};
