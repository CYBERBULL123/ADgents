# Studio UI Reference

Once you boot up `python start.py`, navigate directly to **`http://localhost:8000/studio`**. The frontend application `app.js` handles an immersive glassmorphous interface that interacts live with `server.py` endpoints.

## 1. Dashboard

This provides an overview of the system: connected API health, active agents, populated memory footprints, active skills, etc. 

## 2. Navigating the Agents Hub

You can overview all active Agents under your `/data` folder from the `Agents` tab. 

## 3. Creating & Editing
- From the `Build` tab (or by pressing `✏️ Edit` on an Agent Card), you'll see a form where you assign:
    - **Avatar** & **Role:** The core identity.
    - **Autonomy & Creativity Bars:** Lowering creativity ensures an agent chooses only highly certain steps.
    - **Available Skills Checkboxes:** An agent cannot execute functions that are not checked here.
- The UI transparently updates the backend profile with a JSON `PUT` request dynamically upon saving.

## 4. Chatting vs Tasks
ADgents differentiates between simple chatting and acting structurally:
- **Chat:** Navigating to the `Chat` tab will engage the simple thinking pipeline (e.g. conversational tone, referencing working memory).
- **Run Task:** Typing a complex directive and pressing the `⚡ Run Task` button will divert the session over to the `/tasks` autonomous workspace. A WebSocket channel is immediately established and you'll begin seeing **Thought Steps**, **Actions**, and live JSON payloads the agent utilizes as it interacts with its `Skills`. The step loops will automatically repeat until completion or max iterations.

## 5. Memory Management
If an agent hallucinates a fact, or you wish to directly teach an agent critical background data, you can navigate to the `Memory` tab. 
Here, you can add context directly or review the specific snippets an agent saved from previous chat logs (with visual tags of `Semantic`, `Episodic`, or `Working`).

## 6. Dynamic Skills
By browsing the `Skills` route, users can register new Python methods on the fly, either manually or via **AI Generator**.
- Need a skill that reads Excel spreadsheets? Use the AI generator inside the Studio UI, paste "Parse an xlsx file into dictionary payload", and the UI will automatically craft pure standard-library compliant python handlers.
- See the [Custom Skills](skills.md) guide for writing your own robust tools!
