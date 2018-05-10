new Vue({
    el: '#app',
    data: {
        SERVICE_URL: 'https://sleepy-hamlet-28159.herokuapp.com',
        POLLING_INTERVAL: 2500,
        FILENAME: 'goldvisibility.color.wotmod',
        input: {
            color: '#C000FF'
        },
        disabled: false,
        showSpinner: false,
        showDownloadLink: false,
        actionText: '',
        errors: [],
        blobUrl: undefined,
        edgeBlob: undefined,
        faviconRenderer: undefined
    },
    methods: {
        createJob() {
            this.setSending();

            const options = {method: "POST"};
            if (this.input.file) {
                const formData = new FormData();
                formData.append('file', this.input.file);
                options.body = formData;
            }

            const params = {
                color: !this.input.fillMethod && this.input.file ? undefined : this.input.color,
                luminize: this.input.fillMethod === 'luminize' ? true : undefined
            };

            const query = Object.keys(params).filter(k => {
                return params[k] !== undefined && params[k] !== '';
            }).map(k => {
                return encodeURIComponent(k) + '=' + encodeURIComponent(params[k]);
            }).join('&');

            fetch(this.SERVICE_URL + '/create?' + query, options).then(response => {
                return response.json();
            }).then(obj => {
                if (obj.status === 'error') throw obj.errorMsg;
                location.hash = obj.jobId;
                this.pollStatus(obj.jobId);
            }).catch(this.handleError);
        },
        pollStatus(jobId) {
            fetch(this.SERVICE_URL + '/status/' + jobId).then(response => {
                return response.json();
            }).then(obj => {
                if (obj.status === 'error') throw obj.errorMsg;
                if (obj.status === 'finished') return this.getResult(obj.jobId);
                if (obj.status === 'created') this.setWaiting();
                if (obj.status === 'started') this.setCreating();
                setTimeout(() => this.pollStatus(obj.jobId), this.POLLING_INTERVAL);
            }).catch(this.handleError);
        },
        getResult(jobId) {
            fetch(this.SERVICE_URL + '/download/' + jobId).then(response => {
                this.setDownloading();
                return response.blob();
            }).then(blob => {
                this.reset();
                this.saveBlob(blob);
            }).catch(this.handleError);
        },
        saveBlob(blob) {
            this.showDownloadLink = true;
            const a = this.$refs.downloadLink;
            if (window.navigator.msSaveOrOpenBlob) {
                this.edgeBlob = blob;
            } else {
                this.blobUrl = window.URL.createObjectURL(blob);
                a.href = this.blobUrl;
                a.download = this.FILENAME;
            }
            a.click();
        },
        edgeDownloadFix() {
            if (window.navigator.msSaveOrOpenBlob) window.navigator.msSaveOrOpenBlob(this.edgeBlob, this.FILENAME);
        },
        handleError(error) {
            this.reset();
            this.pushError(error);
        },
        setButtonState(locked) {
            this.showSpinner = !!locked;
            this.disabled = !!locked;
        },
        reset() {
            this.actionText = 'Create';
            this.setButtonState(false);
            location.hash = '';
        },
        setSending() {
            this.showDownloadLink = false;
            if (this.blobUrl) window.URL.revokeObjectURL(this.blobUrl);
            this.actionText = 'Creating job...';
            this.setButtonState(true);
        },
        setWaiting() {
            this.actionText = 'Waiting in queue...';
            this.setButtonState(true);
        },
        setCreating() {
            this.actionText = 'Creating file...';
            this.setButtonState(true);
        },
        setDownloading() {
            this.actionText = 'Downloading...';
            this.setButtonState(true);
        },
        popError(index) {
            this.errors.splice(index, 1);
        },
        pushError(errorMsg) {
            this.errors.push(errorMsg);
        }
    },
    watch: {
        'input.color': {
            immediate: true,
            handler(value) {
                const render = () => {
                    const ctx = this.faviconRenderer.getContext("2d");
                    ctx.beginPath();
                    ctx.rect(0, 0, 16, 16);
                    ctx.fillStyle = value;
                    ctx.fill();
                    document.getElementById('favicon').href = this.faviconRenderer.toDataURL();
                };
                requestAnimationFrame(render);
            }
        }
    },
    created() {
        this.faviconRenderer = document.createElement('canvas');
        this.faviconRenderer.width = 16;
        this.faviconRenderer.height = 16;
        if (location.hash !== undefined && location.hash !== '') {
            this.setWaiting();
            this.pollStatus(location.hash.substring(1));
        } else {
            this.reset();
        }
    }
});