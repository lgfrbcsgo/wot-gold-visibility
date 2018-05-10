Vue.component('color-input', {
    template: `
        <div style="position: relative" ref="colorpicker">
            <div class="input-group">
                <input type="text" class="form-control" :value="displayValue" @input="$emit('input', $event.target.value)" @focus="show" :disabled="disabled">
                <div class="input-group-append" @click="toggle">
                    <span class="input-group-text" style="padding: 0; width: 38px; background-image: url('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAMElEQVQ4T2N89uzZfwY8QFJSEp80A+OoAcMiDP7//483HTx//hx/Ohg1gIFx6IcBALl+VXknOCvFAAAAAElFTkSuQmCC')">
                        <span style="position: relative; border-bottom-right-radius: 3px; border-top-right-radius: 3px; z-index: 1; width: 36px; height: 38px" :style="{'background-color': displayValue}"></span>
                    </span>
                </div>
            </div>
            <div class="arrow" v-show="mustShow" style="z-index: 5; position: absolute; right: 0">
                <color-picker style="font-family: inherit" :value="color" @input="color = $event; $emit('input', displayValue)"></color-picker>
            </div>
        </div>
    `,
    props: {
        value: {
            required: true,
            type: String
        },
        disabled: {
            type: [String, Boolean]
        }
    },
    data: () => ({
        mustShow: false,
        color: {}
    }),
    computed: {
        displayValue() {
            let value = this.color;
            if (value.a === 1) {
                value = value.hex;
            } else if (value.rgba) {
                value = `rgba(${value.rgba.r}, ${value.rgba.g}, ${value.rgba.b}, ${value.a})`;
            }
            return value;
        }
    },
    methods: {
        show() {
            if (this.disabled) return;
            this.mustShow = true;
            document.addEventListener('click', this.handleClick);
        },
        hide() {
            this.mustShow = false;
            document.removeEventListener('click', this.handleClick);
        },
        toggle() {
            this.mustShow ? this.hide() : this.show();
        },
        handleClick(event) {
            const el = this.$refs.colorpicker;
            if (el !== event.target && !el.contains(event.target)) this.hide();
        }
    },
    watch: {
        value: {
            immediate: true,
            handler(value) {
                if (value !== this.displayValue) this.color = value;
            }
        }
    }
});
