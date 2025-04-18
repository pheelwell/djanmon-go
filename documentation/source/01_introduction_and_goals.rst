Introduction and Goals
========================

Djanmongo is a web-based monster battling game built with a Django backend (using Django Rest Framework) and a Vue.js frontend (powered by Vite).

Goals
-----

*   Provide user registration and authentication (JWT-based).
*   Allow users to manage their monster's moveset.
*   Enable users to challenge other online users to battles.
*   Implement a turn-based battle system with unique mechanics:
    *   Dynamic momentum system influencing turn order.
    *   Stat modification stages (Attack, Defense, Speed).
    *   Structured battle logging.
*   Expose game state and actions via a RESTful API. 