import { useState, useEffect, useCallback } from 'react';
import { Typography, Alert } from '@mui/material';
import type { SafetyPolicy } from '../types';
import { listPolicies, createPolicy, updatePolicy, deletePolicy } from '../api';
import PolicyList from '../components/PolicyList';
import PolicyEditor from '../components/PolicyEditor';

type ViewMode = 'list' | 'editor';

export default function PoliciesPage() {
  const [view, setView] = useState<ViewMode>('list');
  const [policies, setPolicies] = useState<SafetyPolicy[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [searchQuery, setSearchQuery] = useState('');
  const [editingPolicy, setEditingPolicy] = useState<SafetyPolicy | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const fetchPolicies = useCallback(async () => {
    try {
      const resp = await listPolicies(searchQuery, page + 1, rowsPerPage);
      setPolicies(resp.policies);
      setTotal(resp.total);
    } catch (err: any) {
      setError('Failed to load policies');
    }
  }, [searchQuery, page, rowsPerPage]);

  useEffect(() => {
    fetchPolicies();
  }, [fetchPolicies]);

  const handleAdd = () => {
    setEditingPolicy(null);
    setView('editor');
  };

  const handleEdit = (policy: SafetyPolicy) => {
    setEditingPolicy(policy);
    setView('editor');
  };

  const handleDelete = async (policy: SafetyPolicy) => {
    try {
      await deletePolicy(policy.id);
      setSuccess(`Policy "${policy.name}" deleted`);
      fetchPolicies();
    } catch {
      setError('Failed to delete policy');
    }
  };

  const handleSave = async (data: {
    name: string;
    description: string;
    policy_content: string;
    is_default: boolean;
    predefined_policy_config: any;
  }) => {
    if (editingPolicy) {
      await updatePolicy(editingPolicy.id, data);
      setSuccess(`Policy "${data.name}" updated`);
    } else {
      await createPolicy(data as any);
      setSuccess(`Policy "${data.name}" created`);
    }
    setView('list');
    fetchPolicies();
  };

  const handleCancel = () => {
    setView('list');
    setEditingPolicy(null);
  };

  return (
    <>
      <Typography variant="h5" sx={{ mb: 3 }}>
        Safety Policies
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}
      {success && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess(null)}>
          {success}
        </Alert>
      )}

      {view === 'list' ? (
        <PolicyList
          policies={policies}
          total={total}
          page={page}
          rowsPerPage={rowsPerPage}
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          onPageChange={setPage}
          onRowsPerPageChange={(rpp) => { setRowsPerPage(rpp); setPage(0); }}
          onEdit={handleEdit}
          onDelete={handleDelete}
          onAdd={handleAdd}
        />
      ) : (
        <PolicyEditor
          policy={editingPolicy}
          onSave={handleSave}
          onCancel={handleCancel}
        />
      )}
    </>
  );
}
