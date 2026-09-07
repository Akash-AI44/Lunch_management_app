// Points the frontend at the backend API. The two are now separate
// projects on separate addresses/ports, so this can no longer default
// to "same origin" — set it explicitly.
//
// Local dev (backend running in Docker on your own machine, published on port 8000):
// window.__API_BASE__ = "http://localhost:8000";        // local dev
// window.__API_BASE__ = "http://192.168.0.146:8000";    // phone testing
window.__API_BASE__ = "https://lunch-management-app-1.onrender.com";  // production
window.__GOOGLE_CLIENT_ID__ = "231823844256-h7888jfjfa0juj800sge48aovur466bk.apps.googleusercontent.com";

// Testing from your phone on the same Wi-Fi? 127.0.0.1 means "this
// device" to a phone, not your computer. Replace it with your
// computer's LAN IP instead, e.g.:
// window.__API_BASE__ = "http://192.168.1.23:8000";
//
// Deploying for real? Point this at wherever the backend actually runs:
// window.__API_BASE__ = "https://api.yourcompany.com";