Vue.component('error-box', {
    template: `
        <div class="alert alert-danger">
            <strong>Error!</strong> {{errorMsg}}
            <button class="close" @click="$emit('close')">
                <span>&times;</span>
            </button>
        </div>
    `,
    props: {
        errorMsg: {
            type: String,
            required: true
        }
    }
});