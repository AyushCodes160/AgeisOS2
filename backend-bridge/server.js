const express = require('express');
const http = require('http');
const socketIo = require('socket.io');

const app = express();
const server = http.createServer(app);
const io = socketIo(server, {
  cors: {
    origin: "*", // Allow all origins for development; adjust for production
    methods: ["GET", "POST"]
  }
});

// Serve static files from the frontend-ui directory (optional, for simplicity)
app.use(express.static('../frontend-ui'));

io.on('connection', (socket) => {
  console.log('A user connected');

  // Handle events from python-core
  socket.on('pending_execution', (data) => {
    // Forward to frontend-ui
    io.emit('pending_execution', data);
  });

  socket.on('blocked_execution', (data) => {
    // Forward to frontend-ui
    io.emit('blocked_execution', data);
  });

  // Handle action_approved from frontend-ui
  socket.on('action_approved', (data) => {
    // Forward to python-core
    io.emit('action_approved', data);
  });

  socket.on('disconnect', () => {
    console.log('User disconnected');
  });
});

const PORT = process.env.PORT || 5000;
server.listen(PORT, () => console.log(`Server running on port ${PORT}`));