import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import './chatStyles.css';

function Chat({ onLogout }) {
    const [message, setMessage] = useState("");
    const [messages, setMessages] = useState([]);
    const chatRef = useRef(null);

    const sendMessage = () => {
        if (!message.trim()) return;

        const newMessage = { from: "user", text: message };
        setMessages(prev => [...prev, newMessage]);

        fetch("http://localhost:5000/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message }),
            credentials: "include"
        })
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                setMessages(prev => [...prev, { from: "bot", text: data.error }]);
            } else {
                setMessages(prev => [...prev, { from: "bot", text: data.reply }]);
            }
        })
        .catch(err => {
            setMessages(prev => [...prev, { from: "bot", text: "Network error" }]);
        });

        setMessage("");
    };

    useEffect(() => {
        if (chatRef.current) {
            chatRef.current.scrollTop = chatRef.current.scrollHeight;
        }
    }, [messages]);

    return (
        <div className="chat-main-container">
            <div className="sidebar">
                <h2>Text Based GPT</h2>
                <div className="profile">
                    <p>😊</p>
                    <span>USER</span>
                </div>
                <button className="logout-btn" onClick={onLogout}>Logout</button>
            </div>

            <div className="center-container">
                <div className="chat-container">
                    <div className="chat-box" ref={chatRef}>
                        {messages.map((msg, index) => (
                            <div key={index} className={`message ${msg.from === "user" ? "sent" : "received"}`}>
                                <strong>{msg.from === "user" ? "You" : "Bot"}:</strong>
                                <div className="message-text">
                                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                        {msg.text}
                                    </ReactMarkdown>
                                </div>
                            </div>
                        ))}
                    </div>
                    <div className="chat-input">
                        <input
                            type="text"
                            value={message}
                            onChange={(e) => setMessage(e.target.value)}
                            placeholder="Type a message..."
                            onKeyPress={(e) => { if (e.key === 'Enter') sendMessage(); }}
                        />
                        <button onClick={sendMessage}>Send</button>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default Chat;
