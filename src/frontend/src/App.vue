<script lang="ts">
import ChatInterface from './components/ChatInterface.vue'
import ThemeSelector from './components/ThemeSelector.vue'
import { ref } from 'vue'

export default {
  name: 'App',
  components: {
    ChatInterface,
    ThemeSelector
  },
  setup() {
    const showSettings = ref(false)
    
    const toggleSettings = () => {
      showSettings.value = !showSettings.value
    }
    
    return {
      showSettings,
      toggleSettings
    }
  }
}
</script>

<template>
  <div class="relative">
    <!-- Settings button -->
    <button 
      @click="toggleSettings" 
      class="fixed top-4 right-4 z-10 btn btn-circle btn-sm"
      aria-label="Settings">
      <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
      </svg>
    </button>
    
    <!-- Settings modal -->
    <div class="modal" :class="{ 'modal-open': showSettings }">
      <div class="modal-box max-h-[90vh] overflow-y-auto">
        <button @click="toggleSettings" class="btn btn-circle btn-sm absolute right-2 top-2">✕</button>
        <ThemeSelector />
      </div>
      <div class="modal-backdrop" @click="toggleSettings"></div>
    </div>
    
    <ChatInterface />
  </div>
</template>

