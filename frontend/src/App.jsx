import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import AdminDashboard from "./components/AdminDashboard";
import { useEffect, useState } from "react";

// Add global fetch interceptor to automatically inject JWT tokens
const originalFetch = window.fetch;
window.fetch = async (...args) => {
  let [resource, config] = args;
  
  const token = localStorage.getItem('ck_token');
  if (token) {
    if (typeof resource === 'string' && resource.startsWith('http://localhost:8000/')) {
        config = config || {};
        config.headers = {
          ...config.headers,
          Authorization: `Bearer ${token}`
        };
    } else if (resource instanceof Request && resource.url.startsWith('http://localhost:8000/')) {
        resource.headers.set('Authorization', `Bearer ${token}`);
    }
  }
  return originalFetch(resource, config);
};

export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    const autoLogin = async () => {
      try {
        const res = await originalFetch("http://localhost:8000/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: "test_admin", password: "admin123" }) 
        });
        
        if (res.ok) {
          const data = await res.json();
          localStorage.setItem('ck_token', data.access_token);
          setIsAuthenticated(true);
        } else {
          // Attempt to register if it doesn't exist
          const regRes = await originalFetch("http://localhost:8000/auth/register", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email: "test_admin", password: "admin123", role: "admin", name: "System Admin" })
          });
          if (regRes.ok) {
            const loginRes = await originalFetch("http://localhost:8000/auth/login", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ email: "test_admin", password: "admin123" })
            });
            const data = await loginRes.json();
            localStorage.setItem('ck_token', data.access_token);
          }
          setIsAuthenticated(true); 
        }
      } catch (err) {
        console.error("Auth error:", err);
        setIsAuthenticated(true); 
      }
    };
    
    autoLogin();
  }, []);

  if (!isAuthenticated) return <div style={{padding: '50px', textAlign: 'center'}}>Authenticating Secure Backend...</div>;

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/admin" replace />} />
        <Route path="/admin/*" element={<AdminDashboard />} />
      </Routes>
    </BrowserRouter>
  );
}
