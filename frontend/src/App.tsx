import { Outlet } from 'react-router-dom';
import { Sidebar } from './components/Sidebar';

export function App() {
  return (
    <>
      <Sidebar />
      <main
        style={{
          flex: 1,
          height: '100vh',
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <Outlet />
      </main>
    </>
  );
} 
 