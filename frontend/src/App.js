import React, { useState, useEffect } from 'react';
import { Routes, Route, useNavigate } from 'react-router-dom';
import Signup from './components/Signup';
import Login from './components/Login';
import Chat from './components/Chat';
import './styles.css';

function App() {
    const [isLoggedIn, setIsLoggedIn] = useState(false);
    const [showAuthPopup, setShowAuthPopup] = useState(false);
    const [authMode, setAuthMode] = useState("login");
    const navigate = useNavigate();

    useEffect(() => {
        fetch("http://localhost:5000/auth/check", {
            credentials: "include"
        })
        .then(res => res.json())
        .then(data => {
            if (data.logged_in) {
                setIsLoggedIn(true);
                navigate("/chat");
            } else {
                setShowAuthPopup(true);
            }
        })
        .catch(() => {
            setShowAuthPopup(true);
        });
    }, []);

    const handleLogin = () => {
        setIsLoggedIn(true);
        setShowAuthPopup(false);
        navigate("/chat");
    };

    const handleLogout = () => {
        fetch("http://localhost:5000/auth/logout", {
            method: "POST",
            credentials: "include"
        }).then(() => {
            setIsLoggedIn(false);
            setShowAuthPopup(true);
            setAuthMode("login");
            navigate("/");
        });
    };

    return (
        <>
            <Routes>
                <Route path="/" element={<div />} />
                <Route path="/signup" element={<Signup onLogin={handleLogin} />} />
                <Route path="/login" element={<Login onLogin={handleLogin} />} />
                <Route path="/chat" element={<Chat onLogout={handleLogout} />} />
            </Routes>

            {showAuthPopup && (
                <div className="auth-popup">
                    <div className="auth-content">
                        <div style={{ marginBottom: '10px' }}>
                            <button onClick={() => setAuthMode("login")} style={{ marginRight: '10px' }}>Login</button>
                            <button onClick={() => setAuthMode("signup")}>Signup</button>
                        </div>
                        {authMode === "login" ? (
                            <Login onLogin={handleLogin} />
                        ) : (
                            <Signup onLogin={handleLogin} />
                        )}
                    </div>
                </div>
            )}
        </>
    );
}

export default App;
