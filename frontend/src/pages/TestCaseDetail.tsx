import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { fetchTestCase, fetchExecutions, fetchComments, createExecution, createComment,
         type TestCase, type Execution, type Comment } from '../lib/api';
import { StatusBadge, PriorityBadge } from '../components/StatusBadge';
import { ArrowLeft, MessageSquare, Play, Clock } from 'lucide-react';

export default function TestCaseDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [tc, setTc] = useState<TestCase | null>(null);
  const [execs, setExecs] = useState<Execution[]>([]);
  const [comments, setComments] = useState<Comment[]>([]);
  const [tab, setTab] = useState<'details' | 'executions' | 'comments'>('details');
  const [newComment, setNewComment] = useState('');
  const [newExecStatus, setNewExecStatus] = useState('pass');
  const [newExecNotes, setNewExecNotes] = useState('');
  const [newExecEnv, setNewExecEnv] = useState('');

  useEffect(() => {
    if (!id) return;
    fetchTestCase(id).then(setTc);
    fetchExecutions(id).then(setExecs);
    fetchComments(id).then(setComments);
  }, [id]);

  const handleAddExec = async () => {
    if (!id) return;
    await createExecution(id, { status: newExecStatus, notes: newExecNotes, environment: newExecEnv });
    fetchExecutions(id).then(setExecs);
    fetchTestCase(id).then(setTc);
    setNewExecNotes(''); setNewExecEnv('');
  };

  const handleAddComment = async () => {
    if (!id || !newComment.trim()) return;
    await createComment(id, { author: 'User', content: newComment });
    fetchComments(id).then(setComments);
    setNewComment('');
  };

  if (!tc) return <div className="p-8 text-slate-400">Loading...</div>;

  return (
    <div className="p-6 space-y-6">
      <button onClick={() => navigate(-1)} className="flex items-center gap-2 text-slate-400 hover:text-slate-200 text-sm">
        <ArrowLeft size={16} /> Back to Test Cases
      </button>

      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-2xl font-bold flex items-center gap-3">
              <span className="font-mono text-blue-400">{tc.id}</span>
              {tc.title}
            </h2>
            <div className="flex items-center gap-3 mt-3">
              <StatusBadge status={tc.status} />
              <PriorityBadge priority={tc.priority} />
              <span className="text-sm text-slate-400">{tc.category}</span>
              {tc.spec_ref && <span className="text-xs font-mono text-slate-500">{tc.spec_ref}</span>}
            </div>
          </div>
        </div>
      </div>

      <div className="flex gap-1 bg-slate-900 border border-slate-800 rounded-lg p-1 w-fit">
        {(['details', 'executions', 'comments'] as const).map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              tab === t ? 'bg-blue-500/20 text-blue-400' : 'text-slate-400 hover:text-slate-200'
            }`}>{t.charAt(0).toUpperCase() + t.slice(1)}{t === 'comments' ? ` (${comments.length})` :
              t === 'executions' ? ` (${execs.length})` : ''}</button>
        ))}
      </div>

      {tab === 'details' && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-4">
          <div><h4 className="text-xs text-slate-500 uppercase mb-1">Description</h4>
            <p className="text-slate-200 whitespace-pre-wrap">{tc.description}</p></div>
          {tc.pass_fail_criteria && <div><h4 className="text-xs text-slate-500 uppercase mb-1">Pass/Fail Criteria</h4>
            <p className="text-slate-200">{tc.pass_fail_criteria}</p></div>}
          <div className="grid grid-cols-3 gap-4">
            <div><h4 className="text-xs text-slate-500 uppercase mb-1">Tool</h4>
              <p className="text-slate-300">{tc.tool || '—'}</p></div>
            <div><h4 className="text-xs text-slate-500 uppercase mb-1">Spec Source</h4>
              <p className="text-slate-300">{tc.spec_source || '—'}</p></div>
            <div><h4 className="text-xs text-slate-500 uppercase mb-1">OCP Req</h4>
              <p className="text-slate-300">{tc.ocp_req_id || '—'}</p></div>
            <div><h4 className="text-xs text-slate-500 uppercase mb-1">Owner</h4>
              <p className="text-slate-300">{tc.owner || '—'}</p></div>
          </div>
        </div>
      )}

      {tab === 'executions' && (
        <div className="space-y-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
            <h4 className="text-sm font-semibold text-slate-300 mb-3 flex items-center gap-2">
              <Play size={16} /> Record Execution</h4>
            <div className="flex gap-3 flex-wrap">
              <select value={newExecStatus} onChange={e => setNewExecStatus(e.target.value)}
                className="bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm text-slate-200">
                <option value="pass">Pass</option><option value="fail">Fail</option>
                <option value="blocked">Blocked</option><option value="skip">Skip</option>
              </select>
              <input placeholder="Environment" value={newExecEnv} onChange={e => setNewExecEnv(e.target.value)}
                className="bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm text-slate-200 flex-1" />
              <input placeholder="Notes" value={newExecNotes} onChange={e => setNewExecNotes(e.target.value)}
                className="bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm text-slate-200 flex-1" />
              <button onClick={handleAddExec}
                className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded text-sm font-medium">
                Record</button>
            </div>
          </div>
          <div className="space-y-2">
            {execs.map(e => (
              <div key={e.id} className="bg-slate-900 border border-slate-800 rounded-lg p-4 flex items-center gap-4">
                <StatusBadge status={e.status} />
                <div className="flex-1">
                  {e.environment && <span className="text-xs text-slate-400 mr-4">{e.environment}</span>}
                  {e.notes && <span className="text-sm text-slate-300">{e.notes}</span>}
                </div>
                <span className="text-xs text-slate-500 flex items-center gap-1">
                  <Clock size={12} /> {e.executed_at ? new Date(e.executed_at).toLocaleString() : '—'}
                </span>
              </div>
            ))}
            {execs.length === 0 && <p className="text-slate-500 text-sm text-center py-8">No executions recorded yet</p>}
          </div>
        </div>
      )}

      {tab === 'comments' && (
        <div className="space-y-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
            <div className="flex gap-3">
              <input placeholder="Add a comment..." value={newComment} onChange={e => setNewComment(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleAddComment()}
                className="bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm text-slate-200 flex-1" />
              <button onClick={handleAddComment}
                className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded text-sm font-medium">
                <MessageSquare size={16} /></button>
            </div>
          </div>
          {comments.map(c => (
            <div key={c.id} className="bg-slate-900 border border-slate-800 rounded-lg p-4">
              <div className="flex justify-between text-xs text-slate-500 mb-2">
                <span className="font-medium text-slate-300">{c.author}</span>
                <span>{c.created_at ? new Date(c.created_at).toLocaleString() : ''}</span>
              </div>
              <p className="text-sm text-slate-200">{c.content}</p>
            </div>
          ))}
          {comments.length === 0 && <p className="text-slate-500 text-sm text-center py-8">No comments yet</p>}
        </div>
      )}
    </div>
  );
}
