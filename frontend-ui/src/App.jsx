import React, { useState, useEffect } from 'react';
import io from 'socket.io-client';

const SOCKET_IO_URL = 'http://localhost:5000'; // Adjust if your backend is on a different host/port

function App() {
  const [socket, setSocket] = useState(null);
  const [status, setStatus] = useState('idle'); // idle, listening, pending, blocked, executing, success, error
  const [script, setScript] = useState('');
  const [request, setRequest] = useState('');
  const [blockedReason, setBlockedReason] = useState('');
  const [executionOutput, setExecutionOutput] = useState('');

  useEffect(() => {
    const newSocket = io(SOCKET_IO_URL);
    setSocket(newSocket);

    newSocket.on('connect', () => {
      console.log('Connected to backend');
      setStatus('idle');
    });

    newSocket.on('pending_execution', (data) => {
      setStatus('pending');
      setScript(data.script);
      setRequest(data.request || '');
    });

    newSocket.on('blocked_execution', (data) => {
      setStatus('blocked');
      setScript(data.script);
      setBlockedReason(data.reason || 'Unknown reason');
    });

    newSocket.on('execution_result', (data) => {
      if (data.success) {
        setStatus('success');
        setExecutionOutput(data.output);
      } else {
        setStatus('error');
        setExecutionOutput(data.output);
      }
    });

    newSocket.on('disconnect', () => {
      console.log('Disconnected from backend');
      setStatus('disconnected');
    });

    return () => {
      newSocket.close();
    };
  }, [SOCKET_IO_URL]);

  const handleApprove = () => {
    if (socket) {
      socket.emit('action_approved', {});
      setStatus('executing');
    }
  };

  // Simulate listening state (in a real app, you might get this from python-core)
  useEffect(() => {
    // For demo, we'll just set to listening when idle and not pending/blocked/etc.
    // In a real implementation, you might have a separate event from python-core for listening state.
    if (status === 'idle') {
      // Optionally set to listening, but we don't have an event for that.
      // We'll leave it as idle and maybe change the UI to indicate listening.
    }
  }, [status]);

  return (
    <div className="p-6 w-full max-w-2xl">
      <h1 className="text-3xl font-bold text-center mb-6">Jarvis Assistant</h1>
      <div className="bg-gray-800 rounded-lg p-4 mb-4">
        <h2 className="text-lg font-semibold mb-2">Status: {status}</h2>
        {status === 'idle' && <p className="text-gray-400">Say "wake up" to activate.</p>}
        {status === 'pending' && (
          <>
            <p className="text-gray-400">Generated script awaiting approval:</p>
            <pre className="bg-gray-700 p-3 rounded mt-2">{script}</pre>
            <button
              onClick={handleApprove}
              className="bg-green-500 hover:bg-green-600 text-white font-bold py-2 px-4 rounded mt-4"
            >
              Approve Execution
            </button>
          </>
        )}
        {status === 'blocked' && (
          <>
            <p className="text-red-400">WARNING: Action Blocked</p>
            <p className="text-gray-400">Reason: {blockedReason}</p>
            <pre className="bg-gray-700 p-3 rounded mt-2">{script}</pre>
          </>
        )}
        {status === 'executing' && <p className="text-yellow-400">Executing approved script...</p>}
        {status === 'success' && (
          <>
            <p className="text-green-400">Execution Successful!</p>
            <pre className="bg-gray-700 p-3 rounded mt-2">{executionOutput}</pre>
          </>
        )}
        {status === 'error' && (
          <>
            <p className="text-red-400">Execution Failed:</p>
            <pre className="bg-gray-700 p-3 rounded mt-2">{executionOutput}</pre>
          </>
        )}
        {status === 'disconnected' && <p className="text-red-400">Disconnected from backend</p>}
      </div>
    </div>
  );
}

export default App;