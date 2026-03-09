import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  LinearProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Stack,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import DangerousIcon from '@mui/icons-material/Dangerous';
import type { SafetyAnalysisResponse } from '../types';

interface Props {
  result: SafetyAnalysisResponse;
}

function getScoreColor(score: number): 'success' | 'warning' | 'error' {
  if (score < 0.3) return 'success';
  if (score < 0.5) return 'warning';
  return 'error';
}

function getProgressColor(score: number): string {
  if (score < 0.3) return '#22c55e';
  if (score < 0.5) return '#f59e0b';
  return '#ef4444';
}

export default function AnalysisResults({ result }: Props) {
  return (
    <Card
      sx={{
        border: result.is_safe
          ? '1px solid rgba(34, 197, 94, 0.4)'
          : '1px solid rgba(239, 68, 68, 0.4)',
        background: result.is_safe
          ? 'linear-gradient(135deg, rgba(34, 197, 94, 0.05), transparent)'
          : 'linear-gradient(135deg, rgba(239, 68, 68, 0.05), transparent)',
      }}
    >
      <CardContent>
        {/* Verdict */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
          {result.is_safe ? (
            <CheckCircleIcon sx={{ fontSize: 40, color: 'success.main' }} />
          ) : (
            <DangerousIcon sx={{ fontSize: 40, color: 'error.main' }} />
          )}
          <Box>
            <Chip
              label={result.is_safe ? 'SAFE' : 'UNSAFE'}
              color={result.is_safe ? 'success' : 'error'}
              sx={{ fontWeight: 700, fontSize: '1rem', px: 2, py: 0.5 }}
            />
            {result.policy_name && (
              <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                Policy: {result.policy_name}
              </Typography>
            )}
          </Box>
          <Box sx={{ ml: 'auto', textAlign: 'right' }}>
            <Typography variant="body2" color="text.secondary">
              Model: {result.model_used}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Inference: {result.inference_time_seconds.toFixed(2)}s
            </Typography>
          </Box>
        </Box>

        {/* Category Scores */}
        <Typography variant="subtitle2" sx={{ mb: 2, color: 'text.secondary' }}>
          Category Scores (violation probability)
        </Typography>
        <Stack spacing={2} sx={{ mb: 2 }}>
          {result.safety_categories.map((cat) => (
            <Box key={cat.category}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                <Typography variant="body2" fontWeight={500}>
                  {cat.category}
                </Typography>
                <Chip
                  label={`${(cat.score * 100).toFixed(1)}%`}
                  size="small"
                  color={getScoreColor(cat.score)}
                  variant="outlined"
                  sx={{ fontWeight: 600, minWidth: 70 }}
                />
              </Box>
              <LinearProgress
                variant="determinate"
                value={cat.score * 100}
                sx={{
                  height: 8,
                  borderRadius: 4,
                  backgroundColor: 'rgba(255,255,255,0.08)',
                  '& .MuiLinearProgress-bar': {
                    borderRadius: 4,
                    backgroundColor: getProgressColor(cat.score),
                  },
                }}
              />
            </Box>
          ))}
        </Stack>

        {/* Raw Output */}
        <Accordion
          sx={{
            background: 'rgba(0,0,0,0.2)',
            '&:before': { display: 'none' },
          }}
        >
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="body2" color="text.secondary">
              Raw Model Output
            </Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Typography
              variant="body2"
              component="pre"
              sx={{
                whiteSpace: 'pre-wrap',
                fontFamily: 'monospace',
                fontSize: '0.8rem',
                color: 'text.secondary',
              }}
            >
              {result.raw_output}
            </Typography>
          </AccordionDetails>
        </Accordion>
      </CardContent>
    </Card>
  );
}
