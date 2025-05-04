import React from 'react';
import Dashboard from './components/Dashboard.jsx';
import { Toaster } from 'react-hot-toast';

// Either create these components or remove them from the render
// import NavBar from './components/NavBar.jsx';
// import Footer from './components/Footer.jsx';

function App() {
  return (
    <div className="min-h-screen bg-gray-100">
      {/* Remove the NavBar and Footer until they're implemented */}
      {/* <NavBar /> */}
      
      <main className="flex-1">
        <Dashboard />
      </main>
      
      {/* <Footer /> */}
      
      {/* Make sure react-hot-toast is installed */}
      <Toaster position="top-right" />
    </div>
  );
}

export default App;
