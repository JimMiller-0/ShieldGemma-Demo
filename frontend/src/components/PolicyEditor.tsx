import { useState, useEffect, useCallback } from 'react';
import {
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  Box,
  Switch,
  FormControlLabel,
  FormGroup,
  Divider,
  Alert,
  CircularProgress,
} from '@mui/material';
import SaveIcon from '@mui/icons-material/Save';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import type { SafetyPolicy, PredefinedPolicyConfig } from '../types';
import { checkPolicyNameExists } from '../api';

interface Props {
  policy?: SafetyPolicy | null;
  onSave: (data: {
    name: string;
    description: string;
    policy_content: string;
    is_default: boolean;
    predefined_policy_config: PredefinedPolicyConfig;
  }) => Promise<void>;
  onCancel: () => void;
}

const PREDEFINED_LABELS: Record<keyof PredefinedPolicyConfig, string> = {
  dangerous_content: 'Dangerous Content',
  harassment: 'Harassment',
  hate_speech: 'Hate Speech',
  sexually_explicit: 'Sexually Explicit',
};

export default function PolicyEditor({ policy, onSave, onCancel }: Props) {
  const isEditing = !!policy;

  const [name, setName] = useState(policy?.name || '');
  const [description, setDescription] = useState(policy?.description || '');
  const [policyContent, setPolicyContent] = useState(policy?.policy_content || '');
  const [isDefault, setIsDefault] = useState(policy?.is_default || false);
  const [predefinedConfig, setPredefinedConfig] = useState<PredefinedPolicyConfig>(
    policy?.predefined_policy_config || {
      dangerous_content: true,
      harassment: true,
      hate_speech: true,
      sexually_explicit: true,
    }
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [nameError, setNameError] = useState<string | null>(null);

  const checkName = useCallback(async (value: string) => {
    if (!value.trim() || (isEditing && value === policy?.name)) {
      setNameError(null);
      return;
    }
    try {
      const exists = await checkPolicyNameExists(value);
      setNameError(exists ? 'A policy with this name already exists' : null);
    } catch {
      // ignore check failures
    }
  }, [isEditing, policy?.name]);

  useEffect(() => {
    const timeout = setTimeout(() => checkName(name), 500);
    return () => clearTimeout(timeout);
  }, [name, checkName]);

  const handleSave = async () => {
    if (!name.trim()) {
      setError('Name is required');
      return;
    }
    if (!policyContent.trim()) {
      setError('Policy content is required');
      return;
    }
    if (nameError) return;

    setSaving(true);
    setError(null);
    try {
      await onSave({
        name: name.trim(),
        description: description.trim(),
        policy_content: policyContent.trim(),
        is_default: isDefault,
        predefined_policy_config: predefinedConfig,
      });
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  const togglePredefined = (key: keyof PredefinedPolicyConfig) => {
    setPredefinedConfig((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
          <Button startIcon={<ArrowBackIcon />} onClick={onCancel}>
            Back
          </Button>
          <Typography variant="h6">
            {isEditing ? 'Edit Policy' : 'Create New Policy'}
          </Typography>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2.5 }}>
          <TextField
            label="Policy Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            error={!!nameError}
            helperText={nameError}
            required
            fullWidth
          />

          <TextField
            label="Description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            multiline
            rows={2}
            fullWidth
          />

          <TextField
            label="Policy Content"
            value={policyContent}
            onChange={(e) => setPolicyContent(e.target.value)}
            multiline
            rows={6}
            required
            fullWidth
            helperText="Define the custom safety policy rules. This will be used in the ShieldGemma prompt as the safety guideline."
          />

          <Divider />

          <FormControlLabel
            control={
              <Switch checked={isDefault} onChange={(e) => setIsDefault(e.target.checked)} />
            }
            label="Set as Default Policy"
          />

          <Box>
            <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>
              Predefined Safety Categories
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ mb: 1.5, display: 'block' }}>
              Toggle which built-in ShieldGemma safety categories to include when using this policy.
            </Typography>
            <FormGroup row>
              {(Object.keys(PREDEFINED_LABELS) as Array<keyof PredefinedPolicyConfig>).map(
                (key) => (
                  <FormControlLabel
                    key={key}
                    control={
                      <Switch
                        checked={predefinedConfig[key]}
                        onChange={() => togglePredefined(key)}
                        size="small"
                      />
                    }
                    label={PREDEFINED_LABELS[key]}
                    sx={{ mr: 3 }}
                  />
                )
              )}
            </FormGroup>
          </Box>

          <Box sx={{ display: 'flex', gap: 2, mt: 1 }}>
            <Button
              variant="contained"
              startIcon={saving ? <CircularProgress size={18} /> : <SaveIcon />}
              onClick={handleSave}
              disabled={saving || !!nameError}
            >
              {saving ? 'Saving...' : isEditing ? 'Update Policy' : 'Create Policy'}
            </Button>
            <Button variant="outlined" onClick={onCancel} disabled={saving}>
              Cancel
            </Button>
          </Box>
        </Box>
      </CardContent>
    </Card>
  );
}
