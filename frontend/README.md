# Fiocruz Variant Browser - Frontend

## Prerequisites

- Node.js (v16 or higher)
- npm (v7 or higher)

## Getting Started

1.  **Install Dependencies**:
    ```bash
    npm install
    ```

2.  **Run Development Server**:
    ```bash
    npm run dev
    ```
    This will start the frontend at `http://localhost:5173`.

3.  **Build for Production**:
    ```bash
    npm run build
    ```
    The output will be in the `dist` directory.

## Project Structure

-   `src/components`: Reusable UI components (Header, Charts, etc.).
-   `src/hooks`: Custom hooks for logic (useSearch).
-   `src/api`: API client configuration.
-   `src/index.css`: Tailwind CSS configuration.

## Configuration

-   **API Proxy**: The `vite.config.js` is configured to proxy API requests (`/variant`, `/gene`, etc.) to `http://localhost:8000`. Ensure your backend is running on this port.
