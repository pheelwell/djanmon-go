# Djanmongo - A Django + Vue Battling Game

## Description

Djanmongo is a web-based monster battling game built with a Django backend (using Django Rest Framework) and a Vue.js frontend (powered by Vite). Players can register, log in, manage their monster's moveset, challenge other users, and engage in turn-based battles featuring a dynamic momentum system.

## Features

*   **User Authentication:** Registration, Login (JWT-based).
*   **Backend:**
    *   Django REST Framework API.
    *   Custom User model with stats (HP, Attack, Defense, Speed, Level).
    *   Attack model defining various moves (damage, stat changes, healing).
    *   Battle model tracking game state (players, status, HP, momentum, stat stages, turn log).
    *   Turn-based battle logic (`battle_logic.py`) handling core actions.
    *   API endpoints for user profiles, attacks, battle initiation/response, active battle state, and battle actions.
*   **Frontend (Vue.js with Vite & Pinia):**
    *   User profile display.
    *   Moveset Management:
        *   Drag-and-drop interface (`vuedraggable`) to select up to 6 moves.
        *   Saving selected moveset to the backend.
    *   Challenging other online users.
    *   Accepting/Declining battle challenges.
    *   Real-time Battle View (`BattleView.vue`):
        *   Displays player/opponent stats, HP bars, and current stat stages.
        *   Visual Momentum Bar with perspective flipping and rescaling for high values.
        *   Momentum gain preview with uncertainty range visualization.
        *   Displays the user's *selected* attacks for action choice (grayed out when not user's turn).
        *   Structured battle log with source highlighting and effect styling (damage, heal, stat changes, faint).
        *   Polling for battle state updates.
    *   State management with Pinia (`authStore`, `gameStore`).
    *   API client (`axios`) with interceptors for auth headers and auto-logout on 401 errors.
*   **Management Command:** `add_attacks` to populate/update attack data.

## Tech Stack

*   **Backend:** Python, Django, Django Rest Framework
*   **Frontend:** Vue.js 3 (Composition API), Vite, Pinia, Vue Router, `vuedraggable`, Axios
*   **Database:** SQLite (default, configured in Django)

## Setup & Installation

1.  **Clone the Repository:**
    ```bash
    git clone <your-repository-url>
    cd djanmongo 
    ```

2.  **Backend Setup (Django):**
    *   Create and activate a Python virtual environment:
        ```bash
        python -m venv .venv
        # On Windows
        # .venv\Scripts\activate 
        # On macOS/Linux
        source .venv/bin/activate 
        ```
    *   Install Python dependencies:
        ```bash
        pip install -r requirements.txt 
        # (Assuming you have a requirements.txt file)
        # If not, you'll need to manually install Django, djangorestframework, djangorestframework-simplejwt etc.
        ```
    *   Apply database migrations:
        ```bash
        python manage.py migrate
        ```
    *   (Optional) Populate initial attack data:
        ```bash
        python manage.py add_attacks
        ```
    *   (Optional) Create a superuser for admin access:
        ```bash
        python manage.py createsuperuser
        ```

3.  **Frontend Setup (Vue):**
    *   Navigate to the frontend directory:
        ```bash
        cd frontend
        ```
    *   Install Node.js dependencies:
        ```bash
        npm install 
        # or yarn install or pnpm install depending on your setup
        ```
    *   Navigate back to the project root:
        ```bash
        cd ..
        ```

## Running the Project

1.  **Start the Backend Server:**
    *   Make sure your virtual environment is activated.
    *   From the project root directory (`djanmongo/`), run:
        ```bash
        python manage.py runserver
        ```
    *   The backend API will typically be available at `http://127.0.0.1:8000/`.

2.  **Start the Frontend Development Server:**
    *   Open a *new* terminal.
    *   Navigate to the frontend directory:
        ```bash
        cd frontend
        ```
    *   Run the development server:
        ```bash
        npm run dev
        # or yarn dev or pnpm dev
        ```
    *   The frontend application will typically be available at `http://localhost:5173/` (or another port specified by Vite).

## Usage

1.  Open the frontend URL in your browser.
2.  Register a new user or log in with existing credentials.
3.  Navigate to the "Manage Moveset" section (likely from the home view) to select your attacks.
4.  Challenge another user from the user list on the home view.
5.  If challenged, accept or decline the battle from the pending requests area (logic might need adding/refining).
6.  Once a battle starts, select your moves when it's your turn and watch the momentum shift!

## Battle Mechanics

The core battle logic (`game/battle_logic.py`) involves the following:

*   **Damage Calculation:** Uses a simplified formula based on the attacker's modified Attack, the target's modified Defense, and the move's Power. A random factor (85%-100%) adds slight variability.
*   **Stat Stages:** Attack, Defense, and Speed can be modified during battle (from -6 to +6). Each stage applies a multiplier to the base stat (e.g., +1 stage = 1.5x, -1 stage = 0.66x).
*   **HP Changes:** Moves can directly heal the user or damage the user/target (e.g., recoil).
*   **Momentum Gain:** Using an attack grants momentum based on its `momentum_cost`:
    *   **Speed Influence:** The attacker's current Speed (including stat stages) relative to a baseline scales the *potential* gain range (clamped between 0.33x and 3.0x the base cost).
    *   **Uncertainty:** The final gain is a random integer between 25% and 100% of the speed-adjusted potential gain range.
*   **Turn Switching:** After an action, if the attacker's total momentum is greater than the opponent's, the turn passes to the opponent. Otherwise, the attacker may get another turn.
*   **Battle Log:** A structured log records every significant action, including move usage, damage dealt, HP changes, stat modifications, momentum gains, and turn changes.
