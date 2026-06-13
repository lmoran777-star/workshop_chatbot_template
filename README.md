# Workshop Chatbot Template

A simple chatbot template for a 90-minute generative AI workshop.

Students personalize the bot by editing JSON files, adding company documents, adding a logo, and turning tools on/off from the interface. The app runs with Streamlit and calls CompactifAI using an OpenAI-compatible chat completions endpoint.

## What students edit

```text
config/
  company.json        -> company name, bot name, goal, target users
  personality.json    -> tone, role, style, safety rules
  tools.json          -> default tools enabled/disabled
  model.json          -> model, temperature, max tokens

company_data/
  Put PDFs, DOCX, TXT, MD, CSV, or JSON files here

company_logo/
  Put one PNG, JPG, JPEG, or WEBP logo image here

app.py                -> the app code, only edit this if you want to go further
```

## New workshop features

The app now shows after every assistant answer:

- model response time,
- prompt tokens,
- completion tokens,
- total tokens,
- model used,
- number of tools sent to the model,
- which tools were actually called.

When the API returns official `usage` fields, the app shows real API usage. If usage is not returned, or if the app is in demo mode, it shows an estimated token count so students can still compare behavior.

Students can also turn tools on/off directly from the sidebar. This is useful for comparing the same question with and without tools.

## Fast local run

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Online run for students

Recommended workshop route:

1. Create a GitHub repository from this template.
2. Students edit files directly in GitHub's web interface.
3. Deploy the repository on Streamlit Community Cloud.
4. Add the CompactifAI API key in Streamlit secrets, never inside the code.

Secrets:

```toml
COMPACTIF_API_KEY = "paste-your-key-here"
COMPACTIF_BASE_URL = "https://api.compactif.ai/v1"
```

## Supported models

Use either:

```text
glm-5-1
hypernova-60b
```

The app also accepts common aliases like `glm5-1` and `hypernoba` and maps them to the correct IDs.

## Files students can upload

The app can read:

- `.txt`
- `.md`
- `.json`
- `.csv`
- `.pdf`
- `.docx`

For persistent data, add files to `company_data/` in the repo. For quick testing, use the file uploader inside the app.

## Company logo

To add a permanent logo:

1. Open the `company_logo/` folder in GitHub.
2. Upload one image, preferably named `logo.png`.
3. Redeploy or let Streamlit refresh the app.

Supported logo formats:

```text
.png
.jpg
.jpeg
.webp
```

For a quick class preview, students can also upload a temporary logo from the app sidebar. That preview is not permanent.

## Demo mode

If no API key is configured, the app still opens and explains that it is in demo mode. This is useful for testing the interface before deployment.

## Important warning

This is a workshop prototype. It is not a production customer-support system. Do not put private customer data, passwords, credentials, medical data, bank data, or confidential company data into this demo.
