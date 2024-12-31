from flask import Flask, request, jsonify, send_from_directory, send_file
import subprocess
import threading
import uuid
import os
from datetime import datetime
import zipfile
import traceback

app = Flask(__name__)
RESULTS_DIR = '/app/results'
if not os.path.exists(RESULTS_DIR):
   os.makedirs(RESULTS_DIR)
test_status = {
   "running": False,
   "token": None,
   "start_time": None,
   "end_time": None,
   "result_log": None,
   "process": None,
   "result_file": None,
   "jtl_file": None,
   "html_report": None,
   "html_report_zip": None
}
def run_jmeter(test_plan):
   global test_status
   try:
       # Generate a unique token for the test
       test_status["token"] = str(uuid.uuid4())
       test_status["start_time"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
       test_status["running"] = True
       # Paths for the results, JTL file, and HTML report
       result_file = os.path.join(RESULTS_DIR, f'result_{test_status["token"]}.csv')
       jtl_file = os.path.join(RESULTS_DIR, f'result_{test_status["token"]}.jtl')
       html_report_dir = os.path.join(RESULTS_DIR, f'report_{test_status["token"]}')
       os.makedirs(html_report_dir, exist_ok=True)
       # Construct the command to run the JMeter test
       command = ['jmeter', '-n', '-t', f'/app/git_clones/{test_plan}', '-l', jtl_file, '-j', result_file, '-q', '/app/git_clones/jmeter.properties']
       process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
       test_status["process"] = process
       # Capture output and errors
       stdout, stderr = process.communicate()
       test_status["result_log"] = stdout.decode() + "\n" + stderr.decode()
       # Generate HTML report from JTL file
       report_command = ['jmeter', '-g', jtl_file, '-o', html_report_dir]
       subprocess.run(report_command)
       # Zip the HTML report directory
       html_report_zip = f"{html_report_dir}.zip"
       with zipfile.ZipFile(html_report_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
           for root, dirs, files in os.walk(html_report_dir):
               for file in files:
                   zipf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), html_report_dir))
    # Update test status
       test_status["running"] = False
       test_status["end_time"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
       test_status["result_file"] = result_file
       test_status["jtl_file"] = jtl_file
       test_status["html_report"] = html_report_dir
       test_status["html_report_zip"] = html_report_zip
   except Exception as e:
       # Handle exceptions and update test status
       test_status["running"] = False
       test_status["result_log"] = str(e)
       test_status["end_time"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

@app.route('/start-test', methods=['POST'])
def start_test():
   try:
       if test_status["running"]:
           return jsonify({"error": "Test is already running"}), 400
       data = request.get_json()
       test_plan = data.get('testPlan')
       if not test_plan:
           return jsonify({"error": "testPlan is required"}), 400
       # Check if the test plan file exists in /app/git_clones directory
       test_plan_path = f'/app/git_clones/{test_plan}'
       if not os.path.exists(test_plan_path):
           return jsonify({"error": f"Test plan file '{test_plan}' not found in /app/git_clones directory"}), 404
       # Start the JMeter test in a separate thread
       jmeter_thread = threading.Thread(target=run_jmeter, args=(test_plan,))
       jmeter_thread.start()
       return jsonify({"message": "Test started", "token": test_status["token"]}), 200
   except Exception as e:
       # Log the exception traceback to the console
       traceback.print_exc()
       return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route('/stop-test', methods=['POST'])
def stop_test():
   if not test_status["running"]:
       return jsonify({"error": "No test is running"}), 400
   try:
       process = test_status["process"]
       if process:
           process.terminate()
           test_status["running"] = False
           test_status["end_time"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
           return jsonify({"message": "Test stopped successfully"}), 200
       else:
           return jsonify({"error": "Unable to stop the test process"}), 500
   except Exception as e:
       return jsonify({"error": str(e)}), 500
@app.route('/test-status', methods=['GET'])
def get_test_status():
   return jsonify({
       "status": "Test is running" if test_status["running"] else "No test is running",
       "token": test_status["token"],
       "start_time": test_status["start_time"],
       "end_time": test_status["end_time"],
       "result_file_url": f'/download/{os.path.basename(test_status["result_file"])}' if test_status["result_file"] else '',
       "jtl_file_url": f'/download/{os.path.basename(test_status["jtl_file"])}' if test_status["jtl_file"] else '',
       "view_html_report_url": f'/view-htmlreport/{os.path.basename(test_status["html_report"])}/index.html' if test_status["html_report"] else '',
       "download_html_report_url": f'/download-htmlreport/{os.path.basename(test_status["html_report_zip"])}' if test_status["html_report_zip"] else ''
   }), 200
@app.route('/view-htmlreport/<path:subpath>', methods=['GET'])
def view_htmlreport(subpath):
   return send_from_directory(RESULTS_DIR, subpath)
@app.route('/download-htmlreport/<filename>', methods=['GET'])
def download_htmlreport(filename):
   file_path = os.path.join(RESULTS_DIR, filename)
   if not os.path.exists(file_path):
       return jsonify({"error": "File not found"}), 404
   return send_file(file_path, as_attachment=True)
@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
   file_path = os.path.join(RESULTS_DIR, filename)
   if not os.path.exists(file_path):
       return jsonify({"error": "File not found"}), 404
   return send_file(file_path, as_attachment=True)
@app.route('/health', methods=['GET'])
def health():
   return jsonify({"status": "healthy"}), 200
if __name__ == '__main__':
   app.run(host='0.0.0.0', port=5000)