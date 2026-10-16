import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { MessageSquare, Send, ShieldAlert } from 'lucide-react'
import { feedService, ReelComment } from '@/services/feedService'
import { Button } from '@/components/ui/Button'
import { useAppSelector } from '@/store'

interface ReelCommentsSectionProps {
  reelId: string
  allowComments: boolean
}

export const ReelCommentsSection: React.FC<ReelCommentsSectionProps> = ({
  reelId,
  allowComments,
}) => {
  const queryClient = useQueryClient()
  const { isAuthenticated } = useAppSelector((state) => state.auth)
  const [commentText, setCommentText] = useState('')

  const { data: comments = [], isLoading } = useQuery<ReelComment[]>({
    queryKey: ['reel-comments', reelId],
    queryFn: () => feedService.getComments(reelId),
    enabled: allowComments,
  })

  const postMutation = useMutation({
    mutationFn: (text: string) => feedService.postComment(reelId, text),
    onSuccess: () => {
      setCommentText('')
      queryClient.invalidateQueries({ queryKey: ['reel-comments', reelId] })
    },
  })

  if (!allowComments) {
    return (
      <div className="p-3 bg-stone-50 rounded-xl border border-stone-200 text-stone-500 text-xs text-center">
        Comments are turned off for this offer.
      </div>
    )
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const trimmed = commentText.trim()
    if (!trimmed || trimmed.length > 500) return
    postMutation.mutate(trimmed)
  }

  return (
    <div className="space-y-3 font-sans">
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-bold uppercase tracking-wider text-stone-500 flex items-center gap-1.5">
          <MessageSquare className="w-3.5 h-3.5 text-primary" />
          <span>Customer Inquiries ({comments.length})</span>
        </h4>
        <span className="text-[10px] text-stone-400">Max 500 characters</span>
      </div>

      {/* Comments List */}
      <div className="max-h-40 overflow-y-auto space-y-2 pr-1 no-scrollbar">
        {isLoading ? (
          <p className="text-xs text-stone-400 italic">Loading inquiries...</p>
        ) : comments.length === 0 ? (
          <p className="text-xs text-stone-400 italic">No inquiries yet. Ask about availability below.</p>
        ) : (
          comments.map((c) => (
            <div
              key={c.id}
              className={`p-2.5 rounded-xl border text-xs ${
                c.is_store_reply
                  ? 'bg-amber-50/80 border-amber-200 text-amber-950 ml-3'
                  : 'bg-stone-50 border-stone-200 text-stone-800'
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="font-bold flex items-center gap-1">
                  {c.is_store_reply && (
                    <span className="px-1.5 py-0.2 rounded bg-amber-200 text-amber-800 text-[9px] uppercase font-mono">
                      Store
                    </span>
                  )}
                  {c.user_name}
                </span>
                <span className="text-[10px] text-stone-400">
                  {new Date(c.created_at).toLocaleDateString()}
                </span>
              </div>
              {/* Sanitized Plain Text rendering */}
              <p className="whitespace-pre-wrap break-words">{c.text}</p>
            </div>
          ))
        )}
      </div>

      {/* Comment Input */}
      {isAuthenticated ? (
        <form onSubmit={handleSubmit} className="flex gap-2">
          <input
            type="text"
            value={commentText}
            onChange={(e) => setCommentText(e.target.value.slice(0, 500))}
            placeholder="Ask store a question about this offer..."
            className="flex-1 px-3 py-2 text-xs rounded-xl border border-stone-200 bg-white focus:outline-none focus:ring-1 focus:ring-primary"
            disabled={postMutation.isPending}
          />
          <Button
            type="submit"
            size="sm"
            variant="primary"
            disabled={!commentText.trim() || postMutation.isPending}
            className="h-auto py-1 px-3 text-xs"
          >
            <Send className="w-3.5 h-3.5" />
          </Button>
        </form>
      ) : (
        <p className="text-[11px] text-stone-500 italic">
          Log in to ask the store a question about this offer.
        </p>
      )}

      {postMutation.isError && (
        <p className="text-[10px] text-red-600 flex items-center gap-1">
          <ShieldAlert className="w-3 h-3" />
          Unable to post inquiry. Please try again.
        </p>
      )}
    </div>
  )
}
