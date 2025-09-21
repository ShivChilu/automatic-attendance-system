import React, { useEffect, useState } from "react";
import { api } from "../lib/api";
import { Button } from "./ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "./ui/dialog";

export default function MyMessages({ me }) {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedMessage, setSelectedMessage] = useState(null);
  const [showMessageModal, setShowMessageModal] = useState(false);

  const loadMessages = async () => {
    try {
      setLoading(true);
      const res = await api.get("/messages/personal");
      setMessages(res.data || []);
    } catch (e) {
      console.error("Failed to load messages:", e);
      setMessages([]);
    } finally {
      setLoading(false);
    }
  };

  const markAsRead = async (messageId) => {
    try {
      await api.put(`/messages/${messageId}/read`);
      setMessages(prev => 
        prev.map(msg => 
          msg.id === messageId ? { ...msg, read: true } : msg
        )
      );
    } catch (e) {
      console.error("Failed to mark message as read:", e);
    }
  };

  const openMessage = (message) => {
    setSelectedMessage(message);
    setShowMessageModal(true);
    if (!message.read) {
      markAsRead(message.id);
    }
  };

  useEffect(() => {
    loadMessages();
  }, []);

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="py-4 sm:py-6">
            <h1 className="text-xl sm:text-2xl lg:text-3xl font-bold text-gray-900">
              My Messages
            </h1>
            <p className="mt-1 text-xs sm:text-sm text-gray-600">
              Personal messages from Principal and Co-Admin
            </p>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Messages List */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900">Personal Messages</h3>
            <p className="text-sm text-gray-600 mt-1">
              {messages.length} message{messages.length !== 1 ? 's' : ''} received
            </p>
          </div>
          <div className="divide-y divide-gray-200">
            {loading ? (
              <div className="p-8 text-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
                <p className="text-gray-600">Loading messages...</p>
              </div>
            ) : messages.length === 0 ? (
              <div className="p-8 text-center">
                <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <span className="text-2xl">📩</span>
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">No Messages</h3>
                <p className="text-gray-600">You haven't received any personal messages yet.</p>
              </div>
            ) : (
              messages.map((message) => (
                <div
                  key={message.id}
                  onClick={() => openMessage(message)}
                  className={`p-6 hover:bg-gray-50 cursor-pointer transition-colors ${
                    !message.read ? 'bg-blue-50 border-l-4 border-l-blue-500' : ''
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2 mb-2">
                        <h4 className="text-sm font-semibold text-gray-900 truncate">
                          {message.subject}
                        </h4>
                        {!message.read && (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                            New
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-gray-600 mb-2 line-clamp-2">
                        {message.content}
                      </p>
                      <div className="flex items-center space-x-4 text-xs text-gray-500">
                        <span>From: {message.sender_name}</span>
                        <span>•</span>
                        <span>{formatDate(message.created_at)}</span>
                      </div>
                    </div>
                    <div className="ml-4 flex-shrink-0">
                      <span className="text-gray-400">→</span>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Message Detail Modal */}
        <Dialog open={showMessageModal} onOpenChange={setShowMessageModal}>
          <DialogContent className="sm:max-w-2xl">
            <DialogHeader>
              <DialogTitle>{selectedMessage?.subject}</DialogTitle>
            </DialogHeader>
            {selectedMessage && (
              <div className="py-4">
                <div className="mb-4 p-4 bg-gray-50 rounded-lg">
                  <div className="flex items-center justify-between text-sm text-gray-600 mb-2">
                    <span>From: {selectedMessage.sender_name}</span>
                    <span>{formatDate(selectedMessage.created_at)}</span>
                  </div>
                </div>
                <div className="prose max-w-none">
                  <p className="text-gray-900 whitespace-pre-wrap">
                    {selectedMessage.content}
                  </p>
                </div>
              </div>
            )}
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setShowMessageModal(false)}
              >
                Close
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </div>
  );
}
