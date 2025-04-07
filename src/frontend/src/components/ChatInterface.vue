<script lang="ts">
import axios from "axios";

interface Message {
  role: "user" | "assistant";
  content: string;
}

declare global {
  interface Window {
    __RUNTIME_CONFIG__?: {
      VITE_API_BASE?: string;
    };
  }
}

const apiUrl = window.__RUNTIME_CONFIG__?.VITE_API_BASE || "https://api.manona.ch";

export default {
  name: "ChatInterface",
  data() {
    return {
      messages: [] as Message[],
      newMessage: "",
      isLoading: false,
      dragActive: false,
      selectedFile: null as File | null,
      parsedFileContent: "",
      token: localStorage.getItem("token") || "",
      uploadedFiles: [] as File[],
      isGeneratingReport: false,
    };
  },
  mounted() {
    if (!this.token) {
      this.token = prompt("Please enter your API token:") || "";
      if (this.token) {
        localStorage.setItem("token", this.token);
      }
    }
    console.log("API URL:", apiUrl);
  },
  methods: {
    async parseFile(file: File): Promise<string> {
      const formData = new FormData();
      formData.append("file", file);

      try {
        const response = await axios.post(
          `${apiUrl}/parse-document`,
          formData,
          {
            headers: {
              Authorization: `Bearer ${this.token}`,
            },
          }
        );
        console.log("Parsed file response:", response.data);
        return response.data.text;
      } catch (error) {
        console.error("Error parsing file:", error);
        throw error;
      }
    },

    async sendMessage() {
      if (!this.newMessage.trim() && !this.selectedFile) return;

      // Add user message to chat
      this.messages.push({
        role: "user",
        content: this.selectedFile
          ? `Uploaded file: ${this.selectedFile.name}${
              this.parsedFileContent ? "\n\nContent: " + this.parsedFileContent : ""
            }`
          : this.newMessage,
      });

      // Clear input and file
      this.newMessage = "";
      //const hadFile = !!this.selectedFile;
      this.selectedFile = null;
      this.parsedFileContent = "";

      try {
        this.isLoading = true;
        // Check if token exists
        if (!this.token) {
          this.token = prompt("Please enter your API token:") || "";
          if (this.token) {
            localStorage.setItem("token", this.token);
          } else {
            throw new Error("API token is required");
          }
        }

        console.log("Messages:", this.messages);

        const response = await axios.post(`${apiUrl}/agent`, this.messages, {
          headers: {
            Authorization: `Bearer ${this.token}`,
            "Content-Type": "application/json",
          },
        });

        // Add assistant response to chat
        if (response.data) {
          this.messages.push({
            role: "assistant",
            content: response.data,
          });
        }
      } catch (error) {
        console.error("Error sending message:", error);
        this.messages.push({
          role: "assistant",
          content: "Sorry, there was an error processing your request.",
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
    async handleDrop(e: DragEvent) {
      e.preventDefault();
      this.dragActive = false;

      if (e.dataTransfer?.files.length) {
        const file = e.dataTransfer.files[0];
        if (file.type === "application/pdf") {
          this.selectedFile = file;
          this.startFileProcessing(file);
        } else {
          alert("Please upload only PDF files");
        }
      }
    },
    async handleFileSelect(e: Event) {
      const target = e.target as HTMLInputElement;
      if (target.files?.length) {
        const file = target.files[0];
        this.selectedFile = file;
        this.startFileProcessing(file);
      }
    },
    async startFileProcessing(file: File) {
      try {
        this.isLoading = true;
        this.parsedFileContent = await this.parseFile(file);
        // Store the file for potential report generation
        if (!this.uploadedFiles.some((f) => f.name === file.name)) {
          this.uploadedFiles.push(file);
        }
        // File is now parsed but we don't add it to the messages yet
        // That will happen when the user clicks send
      } catch (error) {
        console.error("Error pre-parsing file:", error);
        alert("There was an error processing your file. Please try again.");
        this.selectedFile = null;
        this.parsedFileContent = "";
      } finally {
        this.isLoading = false;
      }
    },

    async finalizeReport() {
      if (this.uploadedFiles.length === 0) {
        alert("Please upload at least one PDF file before generating a report.");
        return;
      }

      try {
        this.isGeneratingReport = true;

        // For the /finalize-report-form endpoint (multipart/form-data)
        if (false) {
          // Disabled, using JSON endpoint instead
          const formData = new FormData();
          this.uploadedFiles.forEach((file) => {
            formData.append("files", file);
          });
          // Add messages as JSON string
          formData.append("messages", JSON.stringify(this.messages));
          formData.append("title", "Legal Report");

          const response = await axios.post(
            "https://api.manona.ch/finalize-report-form",
            formData,
            {
              headers: {
                Authorization: `Bearer ${this.token}`,
                "Content-Type": "multipart/form-data",
              },
              responseType: "blob",
            }
          );

          this.handleReportDownload(response.data);
        }
        // For the /finalize-report endpoint (JSON payload)
        else {
          // Prepare PDF file data (base64 encoding)
          const pdfFilesData = await Promise.all(
            this.uploadedFiles.map(async (file) => {
              return {
                filename: file.name,
                content: await this.fileToBase64(file),
              };
            })
          );

          const requestBody = {
            messages: this.messages,
            pdf_files: pdfFilesData,
            title: "Legal Report",
          };

          const response = await axios.post(
            `${apiUrl}/finalize-report`,
            requestBody,
            {
              headers: {
                Authorization: `Bearer ${this.token}`,
                "Content-Type": "application/json",
              },
              responseType: "blob",
            }
          );

          this.handleReportDownload(response.data);
        }

        // Add a message to the chat about the finalized report
        this.messages.push({
          role: "user",
          content: "Generated final report from all uploaded documents.",
        });
      } catch (error) {
        console.error("Error generating final report:", error);
        alert("There was an error generating the final report. Please try again.");
      } finally {
        this.isGeneratingReport = false;
      }
    },

    // Helper method to convert File to base64
    fileToBase64(file: File): Promise<string> {
      return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.readAsDataURL(file);
        reader.onload = () => {
          if (typeof reader.result === "string") {
            // Remove data URL prefix (e.g., "data:application/pdf;base64,")
            const base64 = reader.result.split(",")[1];
            resolve(base64);
          } else {
            reject(new Error("Failed to convert file to base64"));
          }
        };
        reader.onerror = (error) => reject(error);
      });
    },

    // Helper method to handle report download
    handleReportDownload(blobData: Blob) {
      const url = window.URL.createObjectURL(new Blob([blobData]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", "final_report.pdf");
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    },
  },
};
</script>

<template>
  <div class="flex flex-col h-screen max-w-4xl mx-auto px-4 py-6">
    <div class="flex-1 overflow-y-auto mb-4 space-y-4">
      <h1 class="text-2xl font-bold mb-4">Manona Demo</h1>
      <p>
        Diese Demo von Manona zeigt, wie ein KI-gestützter Chatbot nach rechtlich
        relevanten Informationen fragt.<br />
        <b
          >🚨 Bitte keine sensiblen Daten einfügen. Bei dieser Demo handelt es sich um
          eine Hackathon-Demo. Verwendung auf eigenes Risiko.</b
        >
      </p>

      <!-- Uploaded files list -->
      <div v-if="uploadedFiles.length > 0" class="card bg-base-200 shadow-sm mb-4">
        <div class="card-body p-3">
          <h2 class="card-title text-sm">Uploaded Documents</h2>
          <ul class="list-disc pl-5 text-sm">
            <li v-for="(file, index) in uploadedFiles" :key="index" class="text-xs">
              {{ file.name }}
            </li>
          </ul>
        </div>
      </div>

      <div
        v-for="(message, index) in messages"
        :key="index"
        :class="['chat', message.role === 'user' ? 'chat-end' : 'chat-start']"
      >
        <div
          :class="[
            'chat-bubble whitespace-pre-wrap',
            message.role === 'user' ? 'chat-bubble-primary' : 'chat-bubble-secondary',
          ]"
        >
          {{ message.content.replace(/ß/g, "ss") }}
        </div>
      </div>
      <div v-if="isLoading" class="loading loading-spinner loading-lg mx-auto"></div>
    </div>

    <div
      class="input-container"
      :class="['card bg-base-200 shadow-xl', { 'border-2 border-primary': dragActive }]"
      @dragenter="handleDragEnter"
      @dragleave="handleDragLeave"
      @dragover.prevent
      @drop="handleDrop"
    >
      <div class="card-body p-4">
        <div
          v-if="selectedFile"
          class="alert mb-2 py-2"
          :class="{
            'alert-info': !parsedFileContent,
            'alert-success': parsedFileContent,
          }"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            class="stroke-current shrink-0 w-6 h-6"
          >
            <path
              v-if="parsedFileContent"
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
            ></path>
            <path
              v-else
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            ></path>
          </svg>
          <span
            >{{ selectedFile.name }}
            <span v-if="parsedFileContent" class="text-xs">(parsed)</span></span
          >
          <div v-if="isLoading" class="loading loading-spinner loading-xs ml-2"></div>
          <button
            class="btn btn-circle btn-ghost btn-xs"
            @click="
              selectedFile = null;
              parsedFileContent = '';
            "
          >
            ✕
          </button>
        </div>

        <textarea
          v-model="newMessage"
          class="textarea textarea-bordered w-full bg-base-100 min-h-[60px] mb-2"
          placeholder="Type your message here or drop a PDF file..."
          @keyup.enter="sendMessage"
        ></textarea>

        <div class="flex justify-between items-center">
          <div class="flex gap-2">
            <label class="btn btn-circle btn-ghost">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                stroke-width="1.5"
                stroke="currentColor"
                class="w-6 h-6"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M18.375 12.739l-7.693 7.693a4.5 4.5 0 01-6.364-6.364l10.94-10.94A3 3 0 1119.5 7.372L8.552 18.32m.009-.01l-.01.01m5.699-9.941l-7.81 7.81a1.5 1.5 0 002.112 2.13"
                />
              </svg>
              <input
                type="file"
                accept=".pdf"
                @change="handleFileSelect"
                class="hidden"
              />
            </label>

            <button
              class="btn btn-outline btn-info"
              @click="finalizeReport"
              :disabled="isGeneratingReport || uploadedFiles.length === 0"
            >
              <span v-if="isGeneratingReport" class="loading loading-spinner"></span>
              <span v-else>Finalize Report</span>
            </button>
          </div>

          <button
            class="btn btn-primary"
            @click="sendMessage"
            :disabled="isLoading || (!newMessage.trim() && !selectedFile)"
          >
            <span v-if="isLoading" class="loading loading-spinner"></span>
            <span v-else>Send</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
