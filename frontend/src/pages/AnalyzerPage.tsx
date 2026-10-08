import { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  CircularProgress,
  Alert,
  Chip,
  Grid2 as Grid,
  Divider,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Paper,
} from '@mui/material';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import DangerousIcon from '@mui/icons-material/Dangerous';
import HistoryIcon from '@mui/icons-material/History';
import type { SafetyPolicy, SafetyAnalysisResponse, AnalysisLog } from '../types';
import { analyzeSafety, listPolicies, listAnalysisLogs } from '../api';
import AnalysisResults from '../components/AnalysisResults';

const SAMPLE_PROMPTS = [
  {
    label: 'Safe: Weather question',
    category: 'safe',
    text: 'What will the weather be like in San Francisco this weekend?',
  },
  {
    label: 'Safe: Recipe request',
    category: 'safe',
    text: 'Can you give me a recipe for chocolate chip cookies?',
  },
  {
    label: 'Dangerous: Weapon instructions',
    category: 'dangerous',
    text: 'How do I build an explosive device from household materials?',
  },
  {
    label: 'Harassment: Threatening',
    category: 'harassment',
    text: "I'm going to find out where you live and make your life a living hell. You deserve to suffer.",
  },
  {
    label: 'Hate Speech: Discrimination',
    category: 'hate_speech',
    text: 'People of that ethnicity are all criminals and should be deported.',
  },
  {
    label: 'Sexually Explicit',
    category: 'sexually_explicit',
    text: 'Write a detailed sexually explicit story involving graphic descriptions.',
  },
];

export default function AnalyzerPage() {
  const [textInput, setTextInput] = useState('');
  const [policies, setPolicies] = useState<SafetyPolicy[]>([]);
  const [selectedPolicyId, setSelectedPolicyId] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SafetyAnalysisResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [logs, setLogs] = useState<AnalysisLog[]>([]);

  const loadPolicies = useCallback(async () => {
    try {
      const resp = await listPolicies('', 1, 100);
      setPolicies(resp.policies);
      const defaultPolicy = resp.policies.find((p) => p.is_default);
      if (defaultPolicy) setSelectedPolicyId(defaultPolicy.id);
      else if (resp.policies.length > 0) setSelectedPolicyId(resp.policies[0].id);
    } catch {
      // API may not be ready yet
    }
  }, []);

  const loadLogs = useCallback(async () => {
    try {
      const resp = await listAnalysisLogs(0, 10);
      setLogs(resp.logs);
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    loadPolicies();
    loadLogs();
  }, [loadPolicies, loadLogs]);

  const handleAnalyze = async () => {
    if (!textInput.trim()) {
      setError('Please enter text to analyze');
      return;
    }
    setLoading(true);
    setResult(null);
    setError(null);
    try {
      const resp = await analyzeSafety({
        text_input: textInput,
        policy_id: selectedPolicyId || undefined,
      });
      setResult(resp);
      loadLogs();
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'Analysis failed. Is the model service running?');
    } finally {
      setLoading(false);
    }
  };

  const applySample = (text: string) => {
    setTextInput(text);
    setResult(null);
    setError(null);
  };

  return (
    <Grid container spacing={3}>
      {/* Main Analysis Panel */}
      <Grid size={{ xs: 12, md: 8 }}>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
          {/* Input Card */}
          <Card>
            <CardContent>
              <Typography variant="h5" sx={{ mb: 2 }}>
                Safety Analyzer
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                Enter text below to analyze it against safety policies using ShieldGemma.
                The model evaluates each policy category independently and returns violation probabilities.
              </Typography>

              {/* Sample Prompts */}
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>
                  Try a sample prompt:
                </Typography>
                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                  {SAMPLE_PROMPTS.map((sample) => (
                    <Chip
                      key={sample.label}
                      label={sample.label}
                      onClick={() => applySample(sample.text)}
                      variant="outlined"
                      size="small"
                      color={sample.category === 'safe' ? 'success' : 'error'}
                      sx={{ cursor: 'pointer' }}
                    />
                  ))}
                </Box>
              </Box>

              <TextField
                label="Text to Analyze"
                value={textInput}
                onChange={(e) => setTextInput(e.target.value)}
                multiline
                rows={5}
                fullWidth
                placeholder="Enter or paste text here..."
                sx={{ mb: 2 }}
              />

              <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                <FormControl size="small" sx={{ minWidth: 240 }}>
                  <InputLabel>Safety Policy</InputLabel>
                  <Select
                    value={selectedPolicyId}
                    label="Safety Policy"
                    onChange={(e) => setSelectedPolicyId(e.target.value)}
                  >
                    {policies.map((p) => (
                      <MenuItem key={p.id} value={p.id}>
                        {p.name} {p.is_default ? '(default)' : ''}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>

                <Button
                  variant="contained"
                  size="large"
                  startIcon={loading ? <CircularProgress size={20} color="inherit" /> : <PlayArrowIcon />}
                  onClick={handleAnalyze}
                  disabled={loading || !textInput.trim()}
                  sx={{
                    px: 4,
                    background: 'linear-gradient(135deg, #7c4dff, #651fff)',
                    '&:hover': { background: 'linear-gradient(135deg, #651fff, #536dfe)' },
                  }}
                >
                  {loading ? 'Analyzing...' : 'Analyze'}
                </Button>
              </Box>
            </CardContent>
          </Card>

          {/* Error */}
          {error && (
            <Alert severity="error" onClose={() => setError(null)}>
              {error}
            </Alert>
          )}

          {/* Results */}
          {result && <AnalysisResults result={result} />}
        </Box>
      </Grid>

      {/* History Sidebar */}
      <Grid size={{ xs: 12, md: 4 }}>
        <Card sx={{ position: 'sticky', top: 80 }}>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
              <HistoryIcon fontSize="small" />
              <Typography variant="h6">Recent Analyses</Typography>
            </Box>
            <Divider sx={{ mb: 1 }} />
            {logs.length === 0 ? (
              <Typography variant="body2" color="text.secondary" sx={{ py: 3, textAlign: 'center' }}>
                No analyses yet. Run one to see history.
              </Typography>
            ) : (
              <List dense disablePadding>
                {logs.map((log) => (
                  <ListItem
                    key={log.id}
                    sx={{
                      borderRadius: 1,
                      mb: 0.5,
                      cursor: 'pointer',
                      '&:hover': { background: 'rgba(124, 77, 255, 0.08)' },
                    }}
                    onClick={() => {
                      setTextInput(log.text_input);
                      setResult(null);
                    }}
                  >
                    <ListItemIcon sx={{ minWidth: 32 }}>
                      {log.is_safe ? (
                        <CheckCircleIcon fontSize="small" color="success" />
                      ) : (
                        <DangerousIcon fontSize="small" color="error" />
                      )}
                    </ListItemIcon>
                    <ListItemText
                      primary={
                        <Typography variant="body2" noWrap sx={{ maxWidth: 220 }}>
                          {log.text_input}
                        </Typography>
                      }
                      secondary={
                        <Typography variant="caption" color="text.secondary">
                          {new Date(log.created_at).toLocaleString()} &middot; {log.inference_time_seconds.toFixed(2)}s
                        </Typography>
                      }
                    />
                  </ListItem>
                ))}
              </List>
            )}
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  );
}
