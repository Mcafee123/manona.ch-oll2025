<template>
    <div class="p-4">
        <h3 class="text-xl font-bold mb-4">Theme Selector</h3>
        <div class="grid grid-cols-2 gap-4">
            <div
                v-for="theme in themes"
                :key="theme"
                class="border rounded-lg p-4 cursor-pointer"
                :data-set-theme="theme"
                @click="setTheme(theme)"
            >
                <div :data-theme="theme" class="text-center font-bold">
                    {{ theme }}
                </div>
            </div>
        </div>
    </div>
</template>

<script>
export default {
    name: 'ThemeSelector',
    data() {
        return {
            themes: ['light', 'dark']
        }
    },
    methods: {
        setTheme(theme) {
            document.documentElement.setAttribute('data-theme', theme)
            localStorage.setItem('theme', theme)
        }
    },
    mounted() {
        const savedTheme = localStorage.getItem('theme')
        if (savedTheme) {
            this.setTheme(savedTheme)
        }
    }
}
</script>
