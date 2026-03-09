import { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  IconButton,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  TextField,
  InputAdornment,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Collapse,
  Tooltip,
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import AddIcon from '@mui/icons-material/Add';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import type { SafetyPolicy } from '../types';

interface Props {
  policies: SafetyPolicy[];
  total: number;
  page: number;
  rowsPerPage: number;
  searchQuery: string;
  onSearchChange: (query: string) => void;
  onPageChange: (page: number) => void;
  onRowsPerPageChange: (rowsPerPage: number) => void;
  onEdit: (policy: SafetyPolicy) => void;
  onDelete: (policy: SafetyPolicy) => void;
  onAdd: () => void;
}

export default function PolicyList({
  policies,
  total,
  page,
  rowsPerPage,
  searchQuery,
  onSearchChange,
  onPageChange,
  onRowsPerPageChange,
  onEdit,
  onDelete,
  onAdd,
}: Props) {
  const [expandedRow, setExpandedRow] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<SafetyPolicy | null>(null);

  const handleDeleteConfirm = () => {
    if (deleteTarget) {
      onDelete(deleteTarget);
      setDeleteTarget(null);
    }
  };

  return (
    <>
      <Card>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
            <TextField
              size="small"
              placeholder="Search policies..."
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && onSearchChange(searchQuery)}
              slotProps={{
                input: {
                  startAdornment: (
                    <InputAdornment position="start">
                      <SearchIcon fontSize="small" />
                    </InputAdornment>
                  ),
                },
              }}
              sx={{ minWidth: 280 }}
            />
            <Box sx={{ flexGrow: 1 }} />
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={onAdd}
            >
              Create New Policy
            </Button>
          </Box>

          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell width={40} />
                  <TableCell>Policy Name</TableCell>
                  <TableCell>Description</TableCell>
                  <TableCell width={120} align="center">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {policies.map((policy) => (
                  <Box component="tbody" key={policy.id}>
                    <TableRow
                      hover
                      sx={{ cursor: 'pointer' }}
                      onClick={() =>
                        setExpandedRow(expandedRow === policy.id ? null : policy.id)
                      }
                    >
                      <TableCell>
                        <IconButton size="small">
                          {expandedRow === policy.id ? (
                            <ExpandLessIcon fontSize="small" />
                          ) : (
                            <ExpandMoreIcon fontSize="small" />
                          )}
                        </IconButton>
                      </TableCell>
                      <TableCell>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Typography fontWeight={500}>{policy.name}</Typography>
                          {policy.is_default && (
                            <Chip label="Default" size="small" color="primary" variant="outlined" />
                          )}
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" color="text.secondary" noWrap sx={{ maxWidth: 400 }}>
                          {policy.description || '—'}
                        </Typography>
                      </TableCell>
                      <TableCell align="center">
                        <Tooltip title="Edit">
                          <IconButton
                            size="small"
                            onClick={(e) => { e.stopPropagation(); onEdit(policy); }}
                          >
                            <EditIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Delete">
                          <IconButton
                            size="small"
                            color="error"
                            onClick={(e) => { e.stopPropagation(); setDeleteTarget(policy); }}
                          >
                            <DeleteIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      </TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell colSpan={4} sx={{ p: 0, border: 0 }}>
                        <Collapse in={expandedRow === policy.id} unmountOnExit>
                          <Box sx={{ p: 2, pl: 8, background: 'rgba(0,0,0,0.15)' }}>
                            <Box sx={{ display: 'flex', gap: 1, mb: 1, alignItems: 'center' }}>
                              <Typography variant="caption" color="text.secondary">
                                ID: {policy.id}
                              </Typography>
                              <Tooltip title="Copy ID">
                                <IconButton
                                  size="small"
                                  onClick={() => navigator.clipboard.writeText(policy.id)}
                                >
                                  <ContentCopyIcon sx={{ fontSize: 14 }} />
                                </IconButton>
                              </Tooltip>
                            </Box>
                            <Typography variant="body2" sx={{ mb: 1, whiteSpace: 'pre-wrap' }}>
                              {policy.policy_content}
                            </Typography>
                            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                              {Object.entries(policy.predefined_policy_config).map(([key, val]) => (
                                <Chip
                                  key={key}
                                  label={key.replace(/_/g, ' ')}
                                  size="small"
                                  color={val ? 'success' : 'default'}
                                  variant={val ? 'filled' : 'outlined'}
                                />
                              ))}
                            </Box>
                            <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                              Created: {new Date(policy.created_at).toLocaleString()}
                            </Typography>
                          </Box>
                        </Collapse>
                      </TableCell>
                    </TableRow>
                  </Box>
                ))}
                {policies.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={4} align="center">
                      <Typography color="text.secondary" sx={{ py: 4 }}>
                        No policies found. Create one to get started.
                      </Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>

          <TablePagination
            component="div"
            count={total}
            page={page}
            onPageChange={(_, newPage) => onPageChange(newPage)}
            rowsPerPage={rowsPerPage}
            onRowsPerPageChange={(e) => onRowsPerPageChange(parseInt(e.target.value, 10))}
            rowsPerPageOptions={[5, 10, 25]}
          />
        </CardContent>
      </Card>

      {/* Delete Confirmation Dialog */}
      <Dialog open={!!deleteTarget} onClose={() => setDeleteTarget(null)}>
        <DialogTitle>Delete Policy</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to delete &quot;{deleteTarget?.name}&quot;? This action cannot be undone.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteTarget(null)}>Cancel</Button>
          <Button onClick={handleDeleteConfirm} color="error" variant="contained">
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
