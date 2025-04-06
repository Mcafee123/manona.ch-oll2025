<script lang="ts">
import axios from 'axios';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

export default {
  name: 'ChatInterface',
  data() {
    return {
      messages: [] as Message[],
      newMessage: '',
      isLoading: false,
      dragActive: false,
      selectedFile: null as File | null,
      token: localStorage.getItem('token') || ''
    }
  },
  mounted() {
    if (!this.token) {
      this.token = prompt('Please enter your API token:') || '';
      if (this.token) {
        localStorage.setItem('token', this.token);
      }
    }
  },
  methods: {
    async sendMessage() {
      if (!this.newMessage.trim() && !this.selectedFile) return;

      // Add user message to chat
      this.messages.push({
        role: 'user',
        content: this.selectedFile 
          ? `Uploaded file: ${this.selectedFile.name}`
          : this.newMessage
      });

      // Clear input and file
      this.newMessage = '';
      this.selectedFile = null;

      try {
        this.isLoading = true;
        // Check if token exists
        if (!this.token) {
          this.token = prompt('Please enter your API token:') || '';
          if (this.token) {
            localStorage.setItem('token', this.token);
          } else {
            throw new Error('API token is required');
          }
        }
        
        const response = await axios.post('http://localhost:8000/agent', this.messages, {
          headers: {
            Authorization: `Bearer ${this.token}`,
            'Content-Type': 'application/json'
          }
        });

        // Add assistant response to chat
        if (response.data) {
          this.messages.push({
            role: 'assistant',
            content: response.data
          });
        }
      } catch (error) {
        console.error('Error sending message:', error);
        this.messages.push({
          role: 'assistant',
          content: 'Sorry, there was an error processing your request.'
        });
      } finally {
        this.isLoading = false;
      }
    },
    handleDragEnter(e: DragEvent) {
      e.preventDefault();
      this.dragActive = true;
    },
    handleDragLeave(e: DragEvent) {
      e.preventDefault();
      this.dragActive = false;
    },
    handleDrop(e: DragEvent) {
      e.preventDefault();
      this.dragActive = false;
      
      if (e.dataTransfer?.files.length) {
        const file = e.dataTransfer.files[0];
        if (file.type === 'application/pdf') {
          this.selectedFile = file;
        } else {
          alert('Please upload only PDF files');
        }
      }
    },
    handleFileSelect(e: Event) {
      const target = e.target as HTMLInputElement;
      if (target.files?.length) {
        this.selectedFile = target.files[0];
      }
    }
  }
}
</script>

<template>
  <div class="flex flex-col h-screen max-w-4xl mx-auto px-4 py-6">
    <div class="flex-1 overflow-y-auto mb-4 space-y-4">
      <div v-for="(message, index) in messages" 
           :key="index" 
           :class="[
             'chat',
             message.role === 'user' ? 'chat-end' : 'chat-start'
           ]">
        <div :class="[
          'chat-bubble',
          message.role === 'user' ? 'chat-bubble-primary' : 'chat-bubble-secondary'
        ]">
          {{ message.content }}
        </div>
      </div>
    </div>
    
    <div class="input-container"
         :class="[
           'card bg-base-200 shadow-xl',
           { 'border-2 border-primary': dragActive }
         ]"
         @dragenter="handleDragEnter"
         @dragleave="handleDragLeave"
         @dragover.prevent
         @drop="handleDrop">
      <div class="card-body p-4">
        <div v-if="selectedFile" class="alert alert-info mb-2 py-2">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="stroke-current shrink-0 w-6 h-6"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
          <span>{{ selectedFile.name }}</span>
          <button class="btn btn-circle btn-ghost btn-xs" @click="selectedFile = null">✕</button>
        </div>
        
        <textarea
          v-model="newMessage"
          class="textarea textarea-bordered w-full bg-base-100 min-h-[60px] mb-2"
          placeholder="Type your message here or drop a PDF file..."
          @keyup.enter="sendMessage"
        ></textarea>
        
        <div class="flex justify-between items-center">
          <label class="btn btn-circle btn-ghost">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6">
              <path stroke-linecap="round" stroke-linejoin="round" d="M18.375 12.739l-7.693 7.693a4.5 4.5 0 01-6.364-6.364l10.94-10.94A3 3 0 1119.5 7.372L8.552 18.32m.009-.01l-.01.01m5.699-9.941l-7.81 7.81a1.5 1.5 0 002.112 2.13" />
            </svg>
            <input
              type="file"
              accept=".pdf"
              @change="handleFileSelect"
              class="hidden"
            >
          </label>
          
          <button 
            class="btn btn-primary"
            @click="sendMessage"
            :disabled="isLoading || (!newMessage.trim() && !selectedFile)">
            <span v-if="isLoading" class="loading loading-spinner"></span>
            <span v-else>Send</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>