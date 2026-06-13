# Deploy online for free: Streamlit Community Cloud

This route avoids VSCode, Cursor, and local setup.

## Teacher preparation

1. Upload this folder to a GitHub repository.
2. Make it a template repository if you want students to copy it easily.
3. Confirm that `app.py`, `requirements.txt`, `config/`, `company_data/`, and `company_logo/` are in the repository root.
4. Create a Streamlit Community Cloud account.
5. Deploy the repository and set the main file path to:

```text
app.py
```

6. Add secrets in Streamlit Cloud:

```toml
COMPACTIF_API_KEY = "your-key"
COMPACTIF_BASE_URL = "https://api.compactif.ai/v1"
```

## Student workflow without local tools

1. Open the GitHub template.
2. Click **Use this template** or fork/copy the repo.
3. Edit the JSON files directly in the GitHub website.
4. Upload company files into `company_data/` using GitHub's **Add file > Upload files**.
5. Upload one logo image into `company_logo/`.
6. Deploy on Streamlit Community Cloud.
7. Add the API key in Streamlit secrets.
8. Test the chatbot, compare tool/token usage, and improve the config.

## Why Streamlit for the workshop?

- It is a simple Python app.
- It has a built-in chat UI.
- It supports file uploads.
- It supports secrets for API keys.
- It can be deployed from GitHub.
- It makes it easy to show response time, token usage, and tool toggles inside the interface.

## Notes about logos and uploaded files

Permanent files should be uploaded to GitHub:

```text
company_data/
company_logo/
```

The app also has temporary uploaders for quick class testing. Temporary uploads are useful for demos but are not saved permanently in the repository.

## Alternative free routes

- Hugging Face Spaces: good for public demos, especially if students already know Hugging Face.
- Render free web service: good for FastAPI/Flask apps, but more technical than Streamlit for this class.
- Replit: very easy for editing online, but free deployment options and limits may vary.
