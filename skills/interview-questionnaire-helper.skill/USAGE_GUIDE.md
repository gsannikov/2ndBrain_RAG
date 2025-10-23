# Interview Questionnaire Helper - Usage Guide

## Overview
Your new skill is ready! This skill helps you prepare for interviews by managing a comprehensive question bank in Notion, crafting thoughtful answers, and practicing with job-specific variations.

## Installation
1. Download the `interview-questionnaire-helper.skill` file
2. In Claude, go to Settings → Skills
3. Click "Add Skill" and upload the .skill file
4. The skill will be available for all your conversations

## Your Notion Page Setup

The skill connects to your page: https://www.notion.so/Tell-Me-about-Yourself-24b1eaaa56f680e49063e57ec9fc739c

### Recommended Page Structure

Organize your questions by motive groups (the skill will help you do this):

```
# Tell Me About Yourself

## Background & Career Journey
### Question: Tell me about yourself
**Guide**: 
- Intent: Understand your professional story
- Framework: Use chronological narrative
- Key Points: Current role, key experiences, why this role
- Pitfalls: Don't recite your resume, keep it concise (1-2 min)

**My Personal Answer**: [Your answer here - the skill will help fill this]

---

## Strengths & Skills
### Question: What are your greatest strengths?
**Guide**:
- Intent: Identify your differentiators
- Framework: 2-3 specific strengths with evidence
- Key Points: Connect to role requirements, give examples
- Pitfalls: Avoid generic answers, don't just list skills

**My Personal Answer**: [Your answer here]

---

[Continue with other question groups...]
```

### Question Groups (Motives):
1. **Background & Career Journey** - Your professional story
2. **Strengths & Skills** - What you bring to the table
3. **Weaknesses & Growth** - Self-awareness and development
4. **Motivation & Goals** - Why you want the role
5. **Problem-Solving & Impact** - How you deliver results
6. **Teamwork & Leadership** - How you work with others
7. **Technical & Domain Expertise** - Role-specific knowledge

## How to Use the Skill

### Mode 1: Fill Initial Data (Building Your Answer Bank)

**When to use**: You have questions but haven't written personal answers yet.

**How to trigger**:
- "Help me fill in my interview answers"
- "Let's work on my Tell Me About Yourself questions"
- "I need to complete my interview questionnaire"

**What happens**:
1. The skill fetches your Notion page
2. Finds questions without answers
3. Works through them one by one:
   - Shows you the question and guide
   - Asks probing questions to draw out details
   - Helps you structure your answer (STAR method, etc.)
   - Gives feedback and suggestions
   - Saves your refined answer to Notion
4. Moves to the next question

**Example conversation**:
```
You: "Help me fill in my interview answers"

Claude: "I'll help you build comprehensive answers for your interview 
questions. Let me fetch your Notion page...

I found 8 questions that need answers. Let's start with the first one:

**Question**: Tell me about yourself

**Guide**: The interviewer wants to understand your professional story. 
Use a chronological narrative covering your current role, key experiences, 
and why you're interested in this role. Keep it to 1-2 minutes.

To help craft your answer, tell me:
1. What's your current role and what do you do?
2. What led you to this career path?
3. What are 2-3 key experiences that shaped your professional journey?"

You: [Provide your thoughts]

Claude: [Asks follow-up questions, helps structure, refines answer, 
then saves to Notion]
```

### Mode 2: Review Questions Before Interview (Practice & Tailor)

**When to use**: You have an interview coming up and want to practice with job-specific focus.

**How to trigger**:
- "I have an interview at [Company] tomorrow, help me practice"
- "Can we review my answers for this specific job?" [include job link]
- "I want to practice interview questions for [role]"

**What happens**:
1. You provide the job posting or describe the role
2. The skill analyzes what the role needs
3. Conducts a mock interview with relevant questions
4. Gives real-time feedback on your answers
5. Suggests how to tailor responses to the job
6. Offers to create a job-specific copy of your answers in Notion

**Example conversation**:
```
You: "I have an interview at Google for a Product Manager role tomorrow. 
Here's the job posting: [link]"

Claude: "Great! I've analyzed the role - Google is looking for someone 
with strong technical collaboration skills, data-driven decision making, 
and experience launching products at scale.

Let me review your existing answers and then we'll do a practice session. 
[Reviews Notion page]

Ready to practice? I'll ask you questions most relevant to this PM role. 
Try to keep your answers to 1-2 minutes and I'll give you feedback.

Let's start with: Tell me about a time you used data to make a product 
decision..."

[After practice session]

Claude: "Strong practice session! A few adjustments for Google specifically:
- Emphasize your cross-functional collaboration more
- Add metrics to your product launch story
- Connect your experience with their focus on user research

Would you like me to create a tailored version of your answers 
specifically for this Google PM interview?"
```

### Mode 3: Additional Questions & Frameworks (Expand Your Prep)

**When to use**: You've completed basic questions and want to add more depth.

**How to trigger**:
- "What other interview questions should I prepare for?"
- "Can you suggest more questions for [tech/consulting/finance] interviews?"
- "Help me expand my question bank for [target company]"

**What happens**:
1. Reviews your current questions
2. Identifies gaps in your preparation
3. Searches for commonly asked questions at target companies/industries
4. Proposes 3-5 strategic additions with explanations
5. Helps you craft answers to new questions (following Mode 1)

**Example conversation**:
```
You: "I've filled in all the basic questions. What else should I prepare 
for tech company interviews?"

Claude: "Let me review your current question bank and identify gaps...

Based on your existing preparation and tech interview trends, I recommend 
adding these 5 questions:

1. **"Why do you want to work in tech?"**
   - Why: Almost universal in tech interviews
   - Gap: You don't have a tech-specific motivation question
   - Category: Motivation & Goals

2. **"Tell me about a time you had to influence without authority"**
   - Why: Critical for tech PMs and eng leads
   - Gap: Your teamwork section lacks an influence example
   - Category: Teamwork & Leadership

3. **"How do you prioritize features with limited resources?"**
   - Why: Common for product/engineering roles
   - Gap: Missing a prioritization framework question
   - Category: Problem-Solving & Impact

[...continues with 2 more questions]

Which questions would you like to add to your Notion page?"

You: "Let's add questions 1, 2, and 3"

Claude: "Great choice! Let's start with 'Why do you want to work in tech?' 
[Begins Mode 1 workflow for each question]"
```

## Tips for Best Results

### For Mode 1 (Filling Answers):
- Take your time - quality over speed
- Provide specific examples with numbers and outcomes
- Don't worry about perfection in the first draft
- Let the skill help you refine and structure
- Save everything to Notion so you can iterate later

### For Mode 2 (Interview Practice):
- Actually say your answers out loud during practice
- Time yourself (aim for 1-2 minutes per answer)
- Ask for honest feedback
- Have the job posting ready to share
- Consider creating tailored copies for multiple companies

### For Mode 3 (Adding Questions):
- Don't add too many at once (3-5 is good)
- Focus on your target industry/role
- Look for questions that complement existing ones
- Research specific companies you're interviewing with

## Frameworks You'll Learn

The skill uses proven interview frameworks:

**STAR Method**:
- **S**ituation: Set the context
- **T**ask: Explain your responsibility
- **A**ction: Describe what you did
- **R**esult: Share the outcome

**PAR Method**:
- **P**roblem: The challenge
- **A**ction: Your approach
- **R**esult: The impact

**CAR Method**:
- **C**hallenge: The difficulty
- **A**ction: What you did
- **R**esult: The outcome

## Common Questions the Skill Covers

The skill includes comprehensive references for:
- Background & career journey questions
- Strengths & weaknesses questions
- Motivation & culture fit questions
- Problem-solving & impact questions
- Teamwork & leadership questions
- Technical & domain-specific questions
- Industry-specific questions (tech, consulting, finance, startups)

## Need Help?

The skill now includes built-in help! Just ask Claude:

### Discovery Commands:
- "What can this skill do?"
- "How do I use this skill?"
- "Show me what modes this skill supports"
- "What frameworks do you use?"
- "Help me get started with interview prep"

### Setup Questions:
- "How do I organize my Notion page?"
- "What structure should my questions follow?"
- "What question groups should I have?"

### Action Commands:
- "Help me fill in my interview answers" (Mode 1)
- "I have an interview at [Company], let's practice" (Mode 2)
- "What other questions should I prepare for?" (Mode 3)
- "Review my answer to [specific question]"

**See QUICK_REFERENCE.md for a printable cheat sheet of all commands!**

The skill is designed to be conversational and adaptive to your needs!
