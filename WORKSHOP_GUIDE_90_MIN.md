# 90-minute workshop guide: Build your own company chatbot

## Learning goal

By the end of the session, each student has a personalized chatbot that:

- has a company idea and clear purpose,
- answers using company data,
- has a defined personality,
- uses at least one optional tool,
- shows token usage and response time,
- has a simple company logo,
- can be deployed online.

## Workshop timing

### 0-10 min: What are we building?

Explain the final result: a small chatbot that can be adapted to any company.

Key concepts:

- Model: generates the answer.
- Personality: instructions that define style and behavior.
- Knowledge/data: files the bot can use as context.
- Tools: actions the bot can call, like calculator or support ticket.
- Tokens: the units the model consumes to read context, tool definitions, and generate answers.
- Deployment: putting the bot online.

Mini prompt for students:

```text
Choose a company or organization. What should your bot help with?
Examples: customer support, internal HR assistant, technician helper, sales assistant, onboarding assistant.
```

### 10-25 min: Choose company and bot goal

Students edit:

```text
config/company.json
```

They should define:

- company name,
- bot name,
- target users,
- product or service,
- bot goal,
- welcome message.

Good examples:

```text
A hotel bot that answers guest questions.
A solar panel technician bot that explains error codes.
An internal HR bot that answers onboarding questions.
A gym bot that helps members choose classes.
```

### 25-40 min: Add company data

Students search online for public information about their chosen company or create their own fictional company data.

They add files to:

```text
company_data/
```

Recommended data formats:

- TXT or Markdown for fastest results,
- PDF for manuals or brochures,
- DOCX for policies or internal documents,
- CSV for product lists or price tables.

Data ideas:

- FAQ,
- service description,
- return policy,
- opening hours,
- technical manual,
- troubleshooting table,
- pricing list,
- safety rules.

Important rule:

```text
Use public or fictional data only. Do not upload private or sensitive data.
```

### 40-50 min: Add branding

Students add a logo image to:

```text
company_logo/
```

Recommended file name:

```text
logo.png
```

They can also use the temporary logo uploader in the app sidebar if they only want to preview the design during class.

### 50-62 min: Design the personality

Students edit:

```text
config/personality.json
```

They choose:

- role,
- tone,
- language,
- answer length,
- do/don't rules,
- safety rules.

Exercise:

Ask the same question with two different personalities and compare the answers.

Example tones:

```text
friendly and simple
luxury and premium
technical and precise
calm and reassuring
funny but professional
```

### 62-78 min: Enable tools and compare token usage

Students can define default tools in:

```text
config/tools.json
```

But during the live workshop, they can also toggle tools directly in the app sidebar.

Available tools:

- `search_company_data`: searches uploaded files.
- `calculator`: calculates prices, percentages, measurements.
- `current_datetime`: knows today's date and time.
- `create_support_ticket`: creates a fake demo support ticket.

Suggested combinations:

```text
Customer support bot: search_company_data + create_support_ticket
Sales bot: search_company_data + calculator
Technical bot: search_company_data + calculator + create_support_ticket
Internal assistant: search_company_data + current_datetime
```

Token experiment:

1. Ask a question with all tools OFF.
2. Ask the same question with relevant tools ON.
3. Compare response time and token count shown under the answer.
4. Discuss why tools can increase token usage: the model receives tool descriptions, may call a tool, then may need another model response to explain the result.

### 78-87 min: Test and improve

Students test with five questions:

1. An easy question from the documents.
2. A question not in the documents.
3. A question requiring a calculation.
4. A question requiring escalation.
5. A question in another language.

They improve the JSON files based on the answers.

### 87-90 min: Share demos

Each student gives a 30-second demo:

```text
My company is...
My bot helps with...
I added these data files...
I chose this personality...
I enabled these tools...
With tools ON/OFF, I saw this token difference...
The best answer I got was...
```

## Teacher checklist

Before class:

- Have the template in GitHub.
- Have a Streamlit Cloud deployment tested.
- Have a demo API key configured.
- Confirm the app displays token usage and response time after answers.
- Confirm logo loading works from `company_logo/`.
- Prepare one example question that clearly shows higher token usage when tools are enabled.
