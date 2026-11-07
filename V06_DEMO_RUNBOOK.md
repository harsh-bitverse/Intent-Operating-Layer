# IOL v0.6 — Engineers' Conclave Demonstration Runbook
## Visual-First Intent Operating Layer

**Baseline:** `v0.6.0`  
**Target Audience:** Evaluators, Engineers, and Conclave Attendees  
**Local Workspace:** `C:\Workspace\Products\Intent Operating Layer`  
**Frontend URL:** `http://127.0.0.1:3000`  
**Backend API:** `http://127.0.0.1:8000`  

---

### 1. System Launch & Health Verification

#### Step 1: Start Backend Server
```powershell
cd "C:\Workspace\Products\Intent Operating Layer"
python -m uvicorn backend.iol.api.app:app --host 127.0.0.1 --port 8000
```
*Expected log:* `Application startup complete. Uvicorn running on http://127.0.0.1:8000`

#### Step 2: Start Frontend Application
```powershell
cd "C:\Workspace\Products\Intent Operating Layer\frontend"
npm run dev -- -p 3000
```
*Expected log:* `Ready in 800ms. Local: http://localhost:3000`

#### Step 3: Verify Core Health
Open `http://localhost:3000` in any Chromium browser (or inspect via curl):
- Top right badge shows: `● Core Online (12 Capabilities)`
- Active authenticated session selector shows: `Demo Operator (Operator)`

---

### 2. Demonstration 1: Autonomous AI Research Workspace (Demo A)

**Objective:** Demonstrate that IOL executes complex research intents, discovers real-world entities, verifies factual claims with cryptographic evidence, and generates a visual, full-screen interactive workspace.

#### Step-by-Step Instructions:
1. In the intent box, type or paste:
   ```text
   Find 3 AI infrastructure startups in India and build an interactive research database
   ```
2. Click **Execute Intent →** (or press Enter).
3. **Observe Immediate Experience Creation ($<5\text{ms}$):**
   - The UI immediately renders the **Adaptive Workspace** tab (`[ ⛶ Adaptive Workspace v0.6 ]`).
   - The top workspace badge displays `[ ⛶ FULL WORKSPACE ]`.
   - The title updates to **"AI Infrastructure Startups Research Workspace"**.
   - Five animated skeleton placeholder rows appear in the database table while background execution begins.
4. **Observe Real-Time Streaming Data Binding:**
   - The **Metric Strip** dynamically tracks execution:
     - `Status: RUNNING` → `Status: COMPLETED`
     - `Execution Mode: LIVE (GITHUB REPOSITORIES API)`
     - `Verified Authentic: 3`
   - As each startup (e.g. *Sarvam AI*, *Krutrim*, *Gnani.ai*) is verified, it binds directly into the table rows.
5. **Interactive Data Grid Features:**
   - **Instant Search:** Type `Sarvam` into the search box; the table immediately filters to matching records.
   - **Column Sorting:** Click the **Confidence** column header to sort by verification score (e.g. 95% down to 85%).
   - **Field-Level Evidence Inspection:** Click any row in the table. The **Field-Level Evidence Drawer** expands, revealing:
     - Verified official website and repository links
     - Source type (`DIRECT_API_FIELD` / `OFFICIAL_WEBSITE`)
     - Cryptographic SHA-256 retrieval provenance
     - Conservative confidence rating
6. **Data Export:**
   - Click **📥 Export CSV** to download `iol_export_YYYY-MM-DD.csv`.
   - Click **📋 Copy JSON** to copy full verified payloads to clipboard.
7. **Full-Screen Immersion:**
   - Click **[ ⛶ Full Workspace ]** in the top right to expand the workspace across the entire viewport. Click **[ ✕ Exit Fullscreen ]** to return.

---

### 3. Demonstration 2: Interactive 2D Neural Network Learning Simulation (Demo B)

**Objective:** Demonstrate that IOL is not limited to search or tabular tasks—it can translate pedagogical intents into interactive, mathematically rigorous visual simulations.

#### Step-by-Step Instructions:
1. In the intent box, type:
   ```text
   Teach me how a neural network learns using an interactive 2D visualization
   ```
2. Click **Execute Intent →**.
3. **Observe Pedagogical Adaptation:**
   - The Experience Engine recognizes the educational intent family and instantiates the `EducationalExplanationRecipe`.
   - The layout presents an **Interactive 2D Neural Network Learning Simulation** with live forward/backward simulation capabilities.
4. **Inspect Neural Network Architecture (2-2-1):**
   - **Input Layer:** 2 neurons ($x_1, x_2$) with feature activation values.
   - **Hidden Layer:** 2 neurons ($h_1, h_2$) with learned biases ($b_1, b_2$).
   - **Output Layer:** 1 neuron ($\hat{y}$) computing the final model prediction.
   - **Synaptic Edges:** Colored connections with weight labels (green for positive weights, red for negative weights).
5. **Interactive Step-by-Step Walkthrough:**
   - Click **Step Forward ▶**:
     - **Step 1:** Feeding inputs into the network.
     - **Step 2:** Computing hidden linear combinations and Sigmoid activation: $h = \sigma(W_1 x + b_1)$.
     - **Step 3:** Calculating prediction $\hat{y}$ and Mean Squared Error Loss: $\text{Loss} = \frac{1}{2}(y - \hat{y})^2 \approx 0.5000$.
     - **Step 4:** Computing backpropagation gradients via the chain rule ($\delta_y = (\hat{y} - y) \cdot \sigma'(z_y)$).
     - **Step 5:** Applying gradient descent updates ($W := W - \eta \nabla_W L$).
   - Observe the green confirmation alert:
     > **🎉 Gradient Descent Convergence: Loss decreased from 0.5000 to 0.0410!**
6. **Controls & Perturbation:**
   - Click **▶ Auto Play** to watch the learning cycle animate automatically.
   - Click **⏮ Reset** to return to Step 1.
   - Drag the feature sliders ($x_1$ and $x_2$) to perturb input values and watch activations update in real-time.

---

### 4. Demonstration 3: Tab Reconnection & Authentic Recorded Replay

**Objective:** Prove that IOL tasks run independently in the background and survive browser crashes, tab closes, or offline disconnects.

#### Step-by-Step Instructions:
1. Start any task (or select an existing completed task from the Task Store sidebar).
2. Note the URL containing `?task_id=task_...` or copy the Task ID.
3. **Close the browser tab entirely** (or refresh the page with Ctrl+R).
4. Reopen `http://localhost:3000/?task_id=<copied_task_id>`.
5. **Observe Instant Recovery:**
   - The application reconnects to the event stream using `Last-Event-ID`.
   - The complete execution history, durable timeline, and interactive workspace state are restored without data loss.
6. **Recorded Replay Distinction:**
   - If historical tasks are replayed from cached fixtures, the **Execution Mode** badge clearly displays:
     `[ 📼 RECORDED REPLAY ]` or `[ ⚠️ FALLBACK REPLAY ]`
   - Demonstrates that IOL never conceals replay modes as live execution.

---

### 5. Automated Verification Commands

To run all automated verification suites before evaluators:

```powershell
# 1. Run All 60 Backend Tests
cd "C:\Workspace\Products\Intent Operating Layer"
python -m pytest backend/tests -v

# 2. Run All 8 Real-Browser Playwright Tests
cd "C:\Workspace\Products\Intent Operating Layer\frontend"
npx playwright test
```
Both suites will report **100% Passing**.
