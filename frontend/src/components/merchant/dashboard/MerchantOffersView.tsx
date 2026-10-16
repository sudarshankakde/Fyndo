import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { PlusCircle, Clock, Eye, AlertCircle, Edit, Trash2, CheckCircle2, RefreshCw, MessageSquare } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Dialog } from '@/components/ui/Dialog'
import { merchantService, MerchantReelItem } from '@/services/merchantService'

interface MerchantOffersViewProps {
  onPostNew: () => void
}

export const MerchantOffersView: React.FC<MerchantOffersViewProps> = ({ onPostNew }) => {
  const queryClient = useQueryClient()
  const [editingReel, setEditingReel] = useState<MerchantReelItem | null>(null)
  const [editTitle, setEditTitle] = useState('')
  const [editAllowComments, setEditAllowComments] = useState(true)
  const [deletingReelId, setDeletingReelId] = useState<string | null>(null)

  const { data: reels = [], isLoading, refetch } = useQuery<MerchantReelItem[]>({
    queryKey: ['merchant-reels'],
    queryFn: () => merchantService.listMyReels(),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, title, allowComments }: { id: string; title: string; allowComments: boolean }) =>
      merchantService.updateReel(id, { title, allow_comments: allowComments }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['merchant-reels'] })
      setEditingReel(null)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => merchantService.deleteReel(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['merchant-reels'] })
      setDeletingReelId(null)
    },
  })

  const handleOpenEdit = (reel: MerchantReelItem) => {
    setEditingReel(reel)
    setEditTitle(reel.title)
    setEditAllowComments(reel.allow_comments)
  }

  const handleSaveEdit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!editingReel || !editTitle.trim()) return
    updateMutation.mutate({
      id: editingReel.id,
      title: editTitle.trim(),
      allowComments: editAllowComments,
    })
  }

  if (isLoading) {
    return (
      <div className="py-20 text-center space-y-3 font-sans">
        <RefreshCw className="w-8 h-8 text-primary animate-spin mx-auto" />
        <p className="text-xs text-stone-500 font-medium">Fetching your store showcase reels...</p>
      </div>
    )
  }

  return (
    <div className="space-y-6 font-sans">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-3 border-b border-stone-200">
        <div>
          <h2 className="text-xl font-extrabold text-stone-900 tracking-tight">Store Deals & Video Reels</h2>
          <p className="text-xs text-stone-500 mt-0.5">
            15–60s vertical promotional reels published to walk-in shoppers around your store.
          </p>
        </div>
        <Button variant="primary" size="sm" onClick={onPostNew} className="text-xs font-bold gap-1.5">
          <PlusCircle className="h-4 w-4" />
          <span>Post New Offer</span>
        </Button>
      </div>

      {reels.length === 0 ? (
        <div className="bg-white rounded-3xl border border-stone-200 p-12 text-center shadow-card space-y-4 max-w-md mx-auto">
          <div className="w-16 h-16 rounded-2xl bg-primary/10 text-primary flex items-center justify-center mx-auto">
            <PlusCircle className="w-8 h-8" />
          </div>
          <div>
            <h3 className="text-lg font-black text-stone-900">No Video Offers Yet</h3>
            <p className="text-xs text-stone-500 mt-1 leading-relaxed">
              Post your first 30-second vertical reel showcasing a signature dish or in-store product discount.
            </p>
          </div>
          <Button onClick={onPostNew} variant="primary" size="md">
            Create First Offer
          </Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {reels.map((reel) => {
            const isApproved = reel.status === 'APPROVED'
            const isPending = reel.status === 'PENDING_MODERATION'
            const isRejected = reel.status === 'REJECTED'

            return (
              <div
                key={reel.id}
                className="bg-white rounded-3xl border border-stone-200/80 p-5 shadow-2xs flex flex-col justify-between space-y-4"
              >
                <div className="space-y-3">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono text-[10px] text-stone-400 font-bold uppercase">
                      ID: {reel.id.slice(0, 8)}
                    </span>
                    {isApproved && <Badge variant="success">Approved & Live</Badge>}
                    {isPending && <Badge variant="amber">Under Review</Badge>}
                    {isRejected && <Badge variant="destructive">Needs Revision</Badge>}
                  </div>

                  {reel.thumbnail_url && (
                    <div className="aspect-[16/9] rounded-2xl overflow-hidden bg-stone-900 relative">
                      <img src={reel.thumbnail_url} alt={reel.title} className="w-full h-full object-cover" />
                      <span className="absolute bottom-2 right-2 px-2 py-0.5 rounded-md bg-black/70 text-white font-mono text-[10px]">
                        {reel.duration_seconds}s
                      </span>
                    </div>
                  )}

                  <h3 className="font-black text-sm text-stone-900 line-clamp-2 leading-snug">{reel.title}</h3>

                  {isRejected && reel.rejection_reason && (
                    <div className="p-2.5 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs">
                      <strong>Rejection reason:</strong> {reel.rejection_reason}
                    </div>
                  )}

                  <div className="flex items-center gap-3 text-xs text-stone-500 pt-1">
                    <span className="flex items-center gap-1 font-mono">
                      <Eye className="w-3.5 h-3.5 text-stone-400" />
                      {reel.views_count} views
                    </span>
                    <span className="flex items-center gap-1">
                      <MessageSquare className="w-3.5 h-3.5 text-stone-400" />
                      {reel.allow_comments ? 'Inquiries Open' : 'Inquiries Off'}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-2 pt-3 border-t border-stone-100">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleOpenEdit(reel)}
                    className="flex-1 text-xs font-bold gap-1"
                  >
                    <Edit className="w-3.5 h-3.5" />
                    Edit
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setDeletingReelId(reel.id)}
                    className="text-xs text-red-600 hover:text-red-700 hover:bg-red-50"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </Button>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Edit Reel Modal */}
      {editingReel && (
        <Dialog
          isOpen={!!editingReel}
          onClose={() => setEditingReel(null)}
          title="Edit Promotional Reel"
          description="Update reel details. Note: Changing live offers may require brief admin re-moderation."
        >
          <form onSubmit={handleSaveEdit} className="space-y-4 text-xs font-sans">
            <div className="p-3 rounded-xl bg-amber-50 border border-amber-200 text-amber-800">
              ⚠️ Editing offer details on a live video may place it in moderation review before updates appear.
            </div>
            <div>
              <label className="font-bold text-stone-700 block mb-1">Offer Title</label>
              <input
                type="text"
                value={editTitle}
                onChange={(e) => setEditTitle(e.target.value)}
                className="w-full px-3 py-2 rounded-xl border border-stone-200 text-xs font-medium focus:ring-1 focus:ring-primary"
                required
              />
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="allowComments"
                checked={editAllowComments}
                onChange={(e) => setEditAllowComments(e.target.checked)}
                className="rounded text-primary focus:ring-primary"
              />
              <label htmlFor="allowComments" className="font-medium text-stone-700">
                Allow customer inquiries on this reel
              </label>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <Button type="button" variant="outline" size="sm" onClick={() => setEditingReel(null)}>
                Cancel
              </Button>
              <Button type="submit" variant="primary" size="sm" disabled={updateMutation.isPending}>
                Save Changes
              </Button>
            </div>
          </form>
        </Dialog>
      )}

      {/* Confirm Deactivate / Delete Modal */}
      {deletingReelId && (
        <Dialog
          isOpen={!!deletingReelId}
          onClose={() => setDeletingReelId(null)}
          title="Confirm Deactivation"
          description="Are you sure you want to remove this promotional reel? Nearby shoppers will no longer see this offer."
        >
          <div className="flex justify-end gap-2 pt-4">
            <Button variant="outline" size="sm" onClick={() => setDeletingReelId(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              size="sm"
              disabled={deleteMutation.isPending}
              onClick={() => deleteMutation.mutate(deletingReelId)}
            >
              Confirm Deactivate
            </Button>
          </div>
        </Dialog>
      )}
    </div>
  )
}
