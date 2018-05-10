Vue.component('color-input-group', {
    template: `
        <div>
            <div class="form-group">
                <color-input v-model="color" :disabled="disabled || (!!file && fillMethod === undefined)"></color-input>
            </div>
            <div class="form-group">
                <label class="btn-link" style="margin: 0 10px 0 0">
                    Upload image <span class="badge badge-secondary">optional</span>
                    <input type="file" ref="fileInput" @change="file = $event.target.files[0]" :disabled="disabled" accept=".png,.tiff,.tga,.dds" style="display: none">
                </label>
                {{fileName}}
                 <span class="fa fa-trash" v-show="!!file" @click="clearFile" style="cursor: pointer"></span>
                <br/>
                <small class="text-muted">Maximum image size: 200 KB, up to 512x512 pixels. PNG is recommended.</small>
            </div>
            <div class="form-group" v-show="!!file">
                <div class="form-check form-check-inline">
                    <label class="form-check-input">
                        <input type="radio" class="form-check-input" :disabled="disabled" :value="undefined" v-model="fillMethod">Do not fill image
                    </label>
                </div>
                <div class="form-check form-check-inline">
                    <label class="form-check-input">
                        <input type="radio" class="form-check-input" :disabled="disabled" value="solid" v-model="fillMethod">Fill with solid color
                    </label>
                </div>
                <div class="form-check form-check-inline">
                    <label class="form-check-input">
                        <input type="radio" class="form-check-input" :disabled="disabled" value="luminize" v-model="fillMethod">Luminize
                    </label>
                </div>
            </div>
        </div>
    `,
    props: {
        value: {
            required: true,
            type: Object
        },
        disabled: {
            default: false,
            type: [String, Boolean]
        }
    },
    computed: {
        color: {
            get() {
                return this.value.color
            },
            set(color) {
                this.update({color: color})
            }
        },
        file: {
            get() {
                return this.value.file
            },
            set(file) {
                this.update({file: file})
            }
        },
        fillMethod: {
            get() {
                return this.value.fillMethod
            },
            set(fillMethod) {
                this.update({fillMethod: fillMethod})
            }
        },
        fileName() {
            if (this.file) return this.file.name;
        }
    },
    methods: {
        update(updates) {
            this.$emit('input', Object.assign({}, this.value, updates));
        },
        clearFile() {
            if (this.disabled) return;
            const input = this.$refs.fileInput;
            input.type = 'text';
            input.type = 'file';
            this.file = undefined;
        }
    }
});
