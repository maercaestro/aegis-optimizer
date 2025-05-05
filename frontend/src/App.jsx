import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import Dashboard from './components/Dashboard';
import FeedstockDeliveryPage from './pages/FeedstockDeliveryPage';

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gray-100">
        <main>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/feedstock" element={<FeedstockDeliveryPage />} />
          </Routes>
        </main>
      </div>
      <Toaster position="top-right" />
    </Router>
  );
}

export default App;
