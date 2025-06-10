from flask import Flask, render_template, request, redirect, url_for, send_from_directory, send_file, abort, session
import joblib
import pandas as pd
import os
from werkzeug.utils import secure_filename

# Inisialisasi Flask dan konfigurasi folder
app = Flask(__name__)
app.secret_key = 'alfinsecretkey'  # wajib untuk session
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv', 'xlsx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Pastikan folder uploads tersedia
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Load model Machine Learning
model = joblib.load('model/random_forest_anomaly_model.joblib')

# Fungsi untuk validasi ekstensi file
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Halaman utama
@app.route('/')
def index():
    return render_template('index.html')

# Halaman tentang
@app.route('/tentang')
def tentang():
    return render_template('about.html')

# Upload dan preview dataset
@app.route('/dataset', methods=['GET', 'POST'])
def dataset():
    table_data = None
    filename = None

    # Upload file
    if request.method == 'POST':
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            session['filename'] = filename  # simpan nama file di session
            return redirect(url_for('dataset', preview=filename))

    # Ambil nama file dari session jika belum ada preview param
    filename = request.args.get('preview') or session.get('filename')

    if filename:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(file_path):
            try:
                if filename.endswith('.csv'):
                    df = pd.read_csv(file_path)
                elif filename.endswith('.xlsx'):
                    df = pd.read_excel(file_path)
                else:
                    df = None
                if df is not None:
                    table_data = df.head(10).to_html(classes='data-table', index=False, border=0)
            except Exception as e:
                table_data = f"<p>Gagal membaca file: {e}</p>"

    return render_template('dataset.html', table_data=table_data, filename=filename)

# Download file terakhir
@app.route('/download')
def download_dataset():
    filename = session.get('filename')
    if not filename:
        abort(404, description="Tidak ada file untuk didownload.")
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        abort(404, description="File tidak ditemukan.")

# Hapus satu file
@app.route('/delete/<filename>', methods=['POST'])
def delete_file(filename):
    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(path):
        os.remove(path)
    if session.get('filename') == filename:
        session.pop('filename', None)
    return redirect(url_for('dataset'))

# Lihat file yang diupload
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Hapus semua file
@app.route('/delete_all', methods=['POST'])
def delete_all_files():
    for filename in os.listdir(app.config['UPLOAD_FOLDER']):
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.isfile(path):
            os.remove(path)
    session.pop('filename', None)
    return redirect(url_for('dataset'))

# Halaman deteksi
@app.route('/deteksi', methods=['GET', 'POST'])
def deteksi():
    result = None

    if request.method == 'POST':
        try:
            data = {
                'timestamp': request.form.get('timestamp'),
                'src_ip_octet': request.form.get('src_ip_octet'),
                'dst_ip_octet': request.form.get('dst_ip_octet'),
                'src_port': int(request.form.get('src_port')),
                'dst_port': int(request.form.get('dst_port')),
                'protocol': request.form.get('protocol'),
                'service': request.form.get('service'),
                'packet_count': int(request.form.get('packet_count')),
                'byte_count': int(request.form.get('byte_count')),
                'duration': float(request.form.get('duration')),
            }

            df_input = pd.DataFrame([data])
            prediction = model.predict(df_input)
            result = "🔴 Anomali Terdeteksi!" if prediction[0] == 1 else "🟢 Lalu lintas Normal."

        except Exception as e:
            result = f"Terjadi kesalahan saat mendeteksi: {e}"

    return render_template('detect.html', result=result)

# Jalankan aplikasi
if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)

