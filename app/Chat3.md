/* =========================================================
   CHAT CONTAINER
========================================================= */
.chat-container {
  display: flex;
  flex-direction: column;
  height: 90vh;
  max-width: 1400px;
  margin: 24px auto;
  background: var(--soft-green-gradient);
  border-radius: 20px;
  box-shadow: 0 10px 30px rgba(0,0,0,0.08);
}

/* =========================================================
   HEADER
========================================================= */
.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px 24px;
  border-bottom: 1px solid var(--border-color);
}

.chat-header h2 {
  margin: 0;
  font-weight: 600;
  color: var(--primary-color-darkest);
}

.header-actions {
  display: flex;
  gap: 12px;
}

/* =========================================================
   MESSAGES
========================================================= */
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 28px 36px;
}

/* =========================================================
   MESSAGE BUBBLES
========================================================= */
.chat-message {
  max-width: 72%;
  padding: 16px 18px;
  border-radius: 18px;
  margin-bottom: 26px;
  position: relative;
  line-height: 1.55;
  animation: fadeIn 0.25s ease-in-out;
}

/* USER */
.chat-message.user {
  margin-left: auto;
  background: var(--success-gradient);
  color: white;
  border-bottom-right-radius: 6px;
}

/* ASSISTANT */
.chat-message.assistant {
  background: var(--white-color);
  border: 1px solid var(--border-color);
  border-bottom-left-radius: 6px;
}

/* ACTIONS */
.message-actions {
  position: absolute;
  right: 8px;
  bottom: -36px;
  display: flex;
  gap: 8px;
  opacity: 0.5;
  transition: opacity 0.2s;
}

.chat-message:hover .message-actions {
  opacity: 1;
}

/* =========================================================
   INPUT ZONE
========================================================= */
.chat-input {
  display: flex;
  gap: 16px;
  padding: 20px 24px;
  border-top: 1px solid var(--border-color);
  background: var(--white-color);
}

.chat-input textarea {
  flex: 1;
  resize: none;
  height: 80px;
  padding: 14px 16px;
  border-radius: 14px;
  border: 1px solid var(--border-color);
  font-size: 16px;
  line-height: 1.4;
}

.chat-input textarea:focus {
  outline: none;
  border-color: var(--primary-color);
  box-shadow: 0 0 0 2px rgba(43,193,129,0.15);
}

.chat-input button {
  min-width: 110px;
  border-radius: 14px;
  font-weight: 600;
  background: var(--success-gradient);
  color: white;
}

/* =========================================================
   THINKING STATE
========================================================= */
.thinking {
  opacity: 0.85;
  font-style: italic;
}

.thinking-bubble {
  display: flex;
  align-items: center;
  color: var(--gray-color-dark);
}

.thinking-text {
  margin-right: 8px;
  font-weight: 500;
}

/* DOTS */
.dots span {
  animation: blink 1.4s infinite both;
  font-weight: bold;
  font-size: 18px;
}

.dots span:nth-child(1) { animation-delay: 0s; }
.dots span:nth-child(2) { animation-delay: 0.2s; }
.dots span:nth-child(3) { animation-delay: 0.4s; }

/* =========================================================
   MATERIAL BUTTON OVERRIDES
========================================================= */
.mat-stroked-button {
  border-color: var(--primary-color);
  color: var(--primary-color-dark);
}

.mat-stroked-button:hover {
  background: rgba(43,193,129,0.08);
}

.mat-icon-button {
  color: var(--primary-color-dark);
}

.mat-icon-button:hover {
  background: rgba(43,193,129,0.12);
}

/* =========================================================
   ANIMATIONS
========================================================= */
@keyframes blink {
  0% { opacity: 0.2; }
  20% { opacity: 1; }
  100% { opacity: 0.2; }
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(6px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* =========================================================
   RESPONSIVE MEDIA QUERIES
========================================================= */

/* 4K / very large screens */
@media (min-width: 1800px) {
  .chat-container {
    max-width: 1600px;
    height: 85vh;
  }
}

/* Desktop */
@media (max-width: 1400px) {
  .chat-container {
    max-width: 1200px;
    height: 90vh;
  }
}

/* Laptop */
@media (max-width: 1200px) {
  .chat-container {
    max-width: 1000px;
    height: 92vh;
  }

  .chat-message {
    max-width: 78%;
  }
}

/* Tablet */
@media (max-width: 992px) {
  .chat-container {
    max-width: 95%;
    height: 95vh;
    margin: 12px auto;
    border-radius: 14px;
  }

  .chat-messages {
    padding: 20px;
  }

  .chat-message {
    max-width: 85%;
  }
}

/* Mobile landscape */
@media (max-width: 768px) {
  .chat-container {
    height: 100vh;
    max-width: 100%;
    margin: 0;
    border-radius: 0;
  }

  .chat-header {
    padding: 14px 16px;
  }

  .chat-message {
    max-width: 92%;
    font-size: 15px;
  }

  .chat-input {
    padding: 14px;
  }
}

/* Mobile portrait */
@media (max-width: 480px) {
  .chat-header h2 {
    font-size: 16px;
  }

  .header-actions {
    gap: 6px;
  }

  .chat-input {
    flex-direction: column;
  }

  .chat-input textarea {
    height: 70px;
    font-size: 14px;
  }

  .chat-input button {
    width: 100%;
  }

  .chat-message {
    max-width: 100%;
  }
}
