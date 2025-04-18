Constraints
===========

Technical Constraints
---------------------

*   **Backend Framework:** Django (>=4.0)
*   **API Framework:** Django REST Framework (>=3.13)
*   **Authentication:** JWT (via djangorestframework-simplejwt >=5.0)
*   **Database:** Configured for PostgreSQL (psycopg2-binary), but initially developed/tested with SQLite (as per README).
*   **Frontend:** Vue.js 3 (Interaction via API, likely requiring CORS handling - `django-cors-headers` is listed).
*   **Lua Integration:** The `lupa` package indicates Lua scripting capabilities are used.
*   **Deployment:** Likely intended for deployment using `gunicorn` and `whitenoise` for static files. 