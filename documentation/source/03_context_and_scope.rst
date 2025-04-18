Context and Scope
=================

System Boundary
---------------

The system consists of:

*   A **Django Backend Application** providing a RESTful API.
*   A **Vue.js Frontend Application** interacting with the backend API.
*   A **Database** (SQLite initially, potentially PostgreSQL) storing user, game, and battle data.
*   External users interacting via the web interface provided by the frontend.

Business Context
----------------

The application provides a platform for users to engage in online monster battles, manage their monster's abilities, and compete against others.

Scope
-----

The current scope includes:

*   User Registration and Login.
*   Moveset Management (selecting attacks).
*   Challenging other users.
*   Accepting/Declining challenges.
*   Turn-based battle execution with:
    *   Damage calculation.
    *   Stat modifications.
    *   Momentum gain and turn switching.
    *   Battle logging.
*   API endpoints for all user-facing features.
*   A management command for populating attack data. 