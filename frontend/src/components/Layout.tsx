import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  AppBar,
  Toolbar,
  Typography,
  Box,
  Tabs,
  Tab,
  Container,
} from '@mui/material';
import SecurityIcon from '@mui/icons-material/Security';

interface LayoutProps {
  children: React.ReactNode;
}

const navItems = [
  { label: 'Analyzer', path: '/' },
  { label: 'Policies', path: '/policies' },
];

export default function Layout({ children }: LayoutProps) {
  const navigate = useNavigate();
  const location = useLocation();

  const currentTab = navItems.findIndex(
    (item) => item.path === location.pathname
  );

  return (
    <Box sx={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <AppBar
        position="sticky"
        elevation={0}
        sx={{
          background: 'linear-gradient(135deg, #0a0e1a 0%, #1a1040 100%)',
          borderBottom: '1px solid rgba(124, 77, 255, 0.2)',
        }}
      >
        <Toolbar>
          <SecurityIcon sx={{ mr: 1.5, color: 'primary.main', fontSize: 28 }} />
          <Typography
            variant="h6"
            sx={{
              background: 'linear-gradient(135deg, #7c4dff, #00e5ff)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              mr: 4,
              fontWeight: 700,
              letterSpacing: '-0.02em',
            }}
          >
            ShieldGemma Demo
          </Typography>
          <Tabs
            value={currentTab === -1 ? 0 : currentTab}
            onChange={(_, newValue) => navigate(navItems[newValue].path)}
            textColor="inherit"
            TabIndicatorProps={{
              sx: { background: 'linear-gradient(90deg, #7c4dff, #00e5ff)', height: 3 },
            }}
          >
            {navItems.map((item) => (
              <Tab key={item.path} label={item.label} sx={{ fontWeight: 600 }} />
            ))}
          </Tabs>
          <Box sx={{ flexGrow: 1 }} />
          <Typography variant="caption" sx={{ color: 'text.secondary' }}>
            Open Source Safety Moderation
          </Typography>
        </Toolbar>
      </AppBar>
      <Container maxWidth="xl" sx={{ flex: 1, py: 4 }}>
        {children}
      </Container>
    </Box>
  );
}
