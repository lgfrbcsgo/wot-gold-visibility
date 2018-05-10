const createButton = $('#button');
const downloadLink = $('#download-link');
const errors = $('#errors');
const fileInput = $('#file-input');
const fileName = $('#file-name');
const removeFile = $('#remove-file');
const fillMethodInputs = $('#fill-method-inputs');
const colorInput = $('#color-input');
colorInput.minicolors({
    format: 'rgb',
    opacity: true,
    theme: 'bootstrap',
    swatches: [
        '#0056FF',
        '#0095FF',
        '#00FFFF',
        '#00F000',
        '#6BFF00',
        '#C000FF',
        '#FF00F4',
        '#FF0000',
        '#FF9000',
        '#FFF700'
    ],
    change: renderFavicon,
    changeDelay: 200
});

const favicon = $('#favicon');
const canvas = document.createElement('canvas');
canvas.width = 16;
canvas.height = 16;

function renderFavicon(value) {
    const ctx = canvas.getContext("2d");
    ctx.beginPath();
    ctx.rect(0, 0, 16, 16);
    ctx.fillStyle = value;
    ctx.fill();
    favicon.attr('href', canvas.toDataURL());
}

let msDownloadHandler = function () {
};
downloadLink.find('a').on('click', function () {
    msDownloadHandler()
});

function saveBlob(blob, fileName) {
    if (window.navigator.msSaveOrOpenBlob) {
        window.navigator.msSaveOrOpenBlob(blob, fileName);
        msDownloadHandler = function () {
            saveBlob(blob, fileName)
        };
    } else {
        const url = window.URL.createObjectURL(blob);
        const a = downloadLink.find('a').get(0);
        a.href = url;
        a.download = fileName;
        a.click();
        window.URL.revokeObjectURL(url);
    }
    downloadLink.show();
}

function pushError(errorMsg) {
    errors.append(`
            <div class="alert alert-danger alert-dismissible" role="alert">
                <button type="button" class="close" data-dismiss="alert" aria-label="Close">
                    <span class="fa fa-close"></span>
                </button>
                <strong>Error!</strong> ${errorMsg}
            </div>
        `);
}

function makeStatus(name, inputDisabled) {
    return function (hash) {
        if (hash !== undefined) {
            location.hash = hash;
        }
        if (this.currentStatus === name) return;
        createButton.button(name);
        createButton.prop('disabled', inputDisabled);
        colorInput.prop('disabled', inputDisabled || ($('input:checked', fillMethodInputs).val() === 'none' && !!fileInput.prop('files')[0]));
        fileInput.prop('disabled', inputDisabled);
        $('input', fillMethodInputs).prop('disabled', inputDisabled);
        removeFile.prop('disabled', inputDisabled);
        this.currentStatus = name;
    };
}

const status = {
    sending: makeStatus('sending', true),
    waiting: makeStatus('waiting', true),
    creating: makeStatus('creating', true),
    downloading: makeStatus('downloading', true),
    reset: makeStatus('create', false, '')
};

function handleError(err) {
    status.reset('');
    pushError(err || 'Something went wrong.');
}

const SERVICE_URL = 'https://sleepy-hamlet-28159.herokuapp.com';

function createJob() {
    status.sending();
    downloadLink.hide();

    const makeBody = file => {
        const formData = new FormData();
        formData.append('file', file);
        return formData;
    };

    const options = {method: "POST"};
    const icon = fileInput.prop('files')[0];
    if (icon) options.body = makeBody(icon);

    const params = {};
    params.color = $('input:checked', fillMethodInputs).val() !== 'none' || !icon ? colorInput.val() : undefined;
    if ($('input:checked', fillMethodInputs).val() === 'luminize' && icon) params.luminize = true;

    const query = Object.keys(params).filter(k => {
        return params[k] !== undefined && params[k] !== '';
    }).map(k => {
        return encodeURIComponent(k) + '=' + encodeURIComponent(params[k]);
    }).join('&');

    fetch(SERVICE_URL + '/create?' + query, options).then(response => {
        return response.json();
    }).then(obj => {
        if (obj.status === 'error') throw obj.errorMsg;
        location.hash = obj.jobId;
        pollStatus(obj.jobId);
    }).catch(handleError);
}

function pollStatus(jobId) {
    fetch(SERVICE_URL + '/status/' + jobId).then(response => {
        return response.json();
    }).then(obj => {
        if (obj.status === 'error') throw obj.errorMsg;

        if (obj.status === 'finished') return getResult(jobId);

        if (obj.status === 'created') status.waiting();
        if (obj.status === 'started') status.creating();
        setTimeout(function () {
            pollStatus(jobId)
        }, 2500);
    }).catch(handleError);
}

function getResult(jobId) {
    fetch(SERVICE_URL + '/download/' + jobId).then(response => {
        status.downloading();
        return response.blob();
    }).then(blob => {
        saveBlob(blob, 'goldvisibility.color.wotmod');
        status.reset('');
    }).catch(handleError);
}

status.reset();
renderFavicon(colorInput.val());
createButton.on('click', createJob);

fileInput.on('change', function () {
    colorInput.prop('disabled', $('input:checked', fillMethodInputs).val() === 'none');
    fileName.text(fileInput.val().split(/(\\|\/)/g).pop());
    removeFile.show();
    fillMethodInputs.show();
});

removeFile.on('click', function () {
    colorInput.prop('disabled', false);
    $('input', fillMethodInputs).first().prop('checked', true);
    fillMethodInputs.hide();
    removeFile.hide();
    fileInput.val('');
    fileName.text('');
});

fillMethodInputs.on('change', function () {
    colorInput.prop('disabled', $('input:checked', fillMethodInputs).val() === 'none');
});

if (location.hash !== undefined && location.hash !== '') {
    status.waiting();
    pollStatus(location.hash.substring(1));
}