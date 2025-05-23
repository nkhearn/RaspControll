import unittest
from unittest.mock import patch, MagicMock, mock_open
from app import app # Your Flask app
from pathlib import Path # For mocking Path.home() if needed
import datetime # For mocking datetime in psutil boot_time

@patch('app.subprocess.run') 
@patch('app.CAMERA_AVAILABLE', False)      
@patch('app.PSUTIL_AVAILABLE', False)      
@patch('app.RPI_GPIO_AVAILABLE', False)    
@patch('app.FILE_MANAGER_REAL_MODE', False) 
class AppTests(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False 
        app.config['SECRET_KEY'] = 'test_secret_key' 
        self.client = app.test_client()

    def test_index_page(self, mock_fm_real_mode, mock_gpio_avail, mock_ps_avail, mock_cam_avail, mock_subprocess_run):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Welcome to RaspControll', response.data)

    def test_gpio_page(self, mock_fm_real_mode, mock_gpio_avail, mock_ps_avail, mock_cam_avail, mock_subprocess_run):
        response = self.client.get('/gpio')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'GPIO Control', response.data)
        response_toggle = self.client.get('/gpio/toggle/17', follow_redirects=True) 
        self.assertEqual(response_toggle.status_code, 200)
        self.assertIn(b'GPIO 17', response_toggle.data)

    def test_file_manager_page(self, mock_fm_real_mode, mock_gpio_avail, mock_ps_avail, mock_cam_avail, mock_subprocess_run):
        response = self.client.get('/file-manager/') 
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'File Manager', response.data)

    def test_ssh_shell_page(self, mock_subprocess_run, mock_cam_avail, mock_ps_avail, mock_gpio_avail, mock_fm_real_mode): 
        response = self.client.get('/ssh')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'SSH Shell</h2>', response.data) 
        
        mock_process_result = MagicMock()
        mock_process_result.stdout = "Simulated ls output: file1.txt directory1"
        mock_process_result.stderr = ""
        mock_process_result.returncode = 0
        mock_subprocess_run.return_value = mock_process_result

        with self.client.session_transaction() as sess: 
            sess['last_command'] = ''
            sess['last_command_output'] = ''
            sess['last_command_error'] = '' 
        response_command = self.client.post('/ssh/command', data={'command': 'ls -simulated'}, follow_redirects=True)
        self.assertEqual(response_command.status_code, 200)
        self.assertIn(b'Simulated ls output: file1.txt directory1', response_command.data) 
        mock_subprocess_run.assert_called_with(
            ['ls', '-simulated'], capture_output=True, text=True, timeout=10, check=False, cwd=str(Path.home())
        )

    def test_system_monitoring_page(self, mock_fm_real_mode, mock_gpio_avail, mock_ps_avail, mock_cam_avail, mock_subprocess_run):
        response = self.client.get('/system-monitoring')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'System Monitoring', response.data)
        self.assertIn(b'CPU Usage', response.data)

    def test_camera_page(self, mock_fm_real_mode, mock_gpio_avail, mock_ps_avail, mock_cam_avail, mock_subprocess_run):
        response = self.client.get('/camera')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Camera Feed', response.data)

    def test_camera_feed_route(self, mock_fm_real_mode, mock_gpio_avail, mock_ps_avail, mock_cam_avail, mock_subprocess_run):
        response = self.client.get('/camera_feed')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'image/png')

    def test_sensors_page(self, mock_fm_real_mode, mock_gpio_avail, mock_ps_avail, mock_cam_avail, mock_subprocess_run):
        response = self.client.get('/sensors')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Sensor Readings', response.data)
        self.assertIn(b'DHT22 Sensor', response.data)

    def test_processes_page(self, mock_fm_real_mode, mock_gpio_avail, mock_ps_avail, mock_cam_avail, mock_subprocess_run):
        response = self.client.get('/processes')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Running Processes', response.data)
        self.assertIn(b'PID', response.data)

    def test_pi_info_page(self, mock_fm_real_mode, mock_gpio_avail, mock_ps_avail, mock_cam_avail, mock_subprocess_run):
        response = self.client.get('/pi-info')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Raspberry Pi Information', response.data)
        self.assertIn(b'Model', response.data)

    def test_pinout_page(self, mock_fm_real_mode, mock_gpio_avail, mock_ps_avail, mock_cam_avail, mock_subprocess_run):
        response = self.client.get('/pinout')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Pinout and Diagrams', response.data)

    def test_pinout_image_route(self, mock_fm_real_mode, mock_gpio_avail, mock_ps_avail, mock_cam_avail, mock_subprocess_run):
        response = self.client.get('/pinout_image')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'image/png')

    def test_notifications_page(self, mock_fm_real_mode, mock_gpio_avail, mock_ps_avail, mock_cam_avail, mock_subprocess_run):
        response = self.client.get('/notifications')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Notifications', response.data)
        with self.client.session_transaction() as sess: pass
        response_add = self.client.post('/notifications/add', data={'message': 'Test notification from unit test'}, follow_redirects=True)
        self.assertEqual(response_add.status_code, 200)
        self.assertIn(b'Test notification from unit test', response_add.data)
        response_clear = self.client.post('/notifications/clear', follow_redirects=True)
        self.assertEqual(response_clear.status_code, 200)
        self.assertNotIn(b'Test notification from unit test', response_clear.data)
        self.assertIn(b'No new notifications.', response_clear.data)

    def test_power_control_page(self, mock_fm_real_mode, mock_gpio_avail, mock_ps_avail, mock_cam_avail, mock_subprocess_run):
        response = self.client.get('/power')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Power Controls', response.data)
        response_shutdown = self.client.post('/power/shutdown', follow_redirects=True)
        self.assertEqual(response_shutdown.status_code, 200)
        self.assertIn(b'Simulated System Shutdown', response_shutdown.data)
        response_reboot = self.client.post('/power/reboot', follow_redirects=True)
        self.assertEqual(response_reboot.status_code, 200)
        self.assertIn(b'Simulated System Reboot', response_reboot.data)


class RealModeAppTests(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['SECRET_KEY'] = 'test_secret_key'
        self.client = app.test_client()

    @patch('app.RPI_GPIO_AVAILABLE', True)
    @patch('app.GPIO', create=True) 
    def test_gpio_page_real_mode(self, mock_GPIO_module, mock_rpi_gpio_available_flag): 
        mock_GPIO_module.BCM = 11 
        mock_GPIO_module.OUT = 0  
        mock_GPIO_module.LOW = 0
        mock_GPIO_module.HIGH = 1
        def mock_gpio_input(pin_id):
            if pin_id == 17: return mock_GPIO_module.HIGH
            if pin_id == 18: return mock_GPIO_module.LOW
            if pin_id == 27: return mock_GPIO_module.LOW
            return mock_GPIO_module.LOW 
        mock_GPIO_module.input.side_effect = mock_gpio_input
        original_controllable_pins = app.CONTROLLABLE_PINS
        app.CONTROLLABLE_PINS = {
            17: {"name": "GPIO 17", "mode": mock_GPIO_module.OUT, "id": 17},
            18: {"name": "GPIO 18", "mode": mock_GPIO_module.OUT, "id": 18},
            27: {"name": "GPIO 27", "mode": mock_GPIO_module.OUT, "id": 27},
        }
        response = self.client.get('/gpio')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'GPIO 17', response.data)
        self.assertIn(b'ON', response.data) 
        self.assertIn(b'GPIO 18', response.data)
        self.assertIn(b'OFF', response.data) 
        self.client.get('/gpio/toggle/17') 
        mock_GPIO_module.output.assert_called_with(17, False) 
        self.client.get('/gpio/toggle/18') 
        mock_GPIO_module.output.assert_called_with(18, True) 
        app.CONTROLLABLE_PINS = original_controllable_pins

    @patch('app.PSUTIL_AVAILABLE', True)
    @patch('app.psutil', create=True) 
    def test_system_monitoring_real_mode(self, mock_psutil, mock_psutil_available_flag): 
        mock_psutil.cpu_percent.return_value = 35.5
        mock_vm = MagicMock(); mock_vm.total = 4 * (1024**3); mock_vm.used = 1 * (1024**3); mock_vm.percent = 25.0
        mock_psutil.virtual_memory.return_value = mock_vm
        mock_disk = MagicMock(); mock_disk.total = 100 * (1024**3); mock_disk.used = 20 * (1024**3); mock_disk.percent = 20.0
        mock_psutil.disk_usage.return_value = mock_disk
        mock_net = MagicMock(); mock_net.bytes_sent = 500 * (1024**2); mock_net.bytes_recv = 100 * (1024**2)
        mock_psutil.net_io_counters.return_value = mock_net
        mock_psutil.boot_time.return_value = datetime.datetime.now().timestamp() - (2 * 24 * 3600 + 3 * 3600 + 30 * 60)
        response = self.client.get('/system-monitoring')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'35.5%', response.data)
        self.assertIn(b'1.00 GB / 4.00 GB (25.0%)', response.data)
        self.assertIn(b'20.00 GB / 100.00 GB (20.0%)', response.data)
        self.assertIn(b'Sent: 500.00 MB', response.data)
        self.assertIn(b'Received: 100.00 MB', response.data)
        self.assertIn(b'2 days, 3 hours, 30 minutes', response.data)

    @patch('app.PSUTIL_AVAILABLE', True)
    @patch('app.psutil', create=True) 
    def test_processes_page_real_mode(self, mock_psutil, mock_psutil_available_flag): 
        mock_proc1_info = {'pid': 101, 'name': 'test_proc1', 'username': 'test_user', 'cpu_percent': 12.3, 'memory_percent': 1.2}
        mock_proc2_info = {'pid': 102, 'name': 'test_proc2', 'username': 'test_user', 'cpu_percent': 0.5, 'memory_percent': 0.5}
        mock_proc1 = MagicMock(); mock_proc1.info = mock_proc1_info
        mock_proc2 = MagicMock(); mock_proc2.info = mock_proc2_info
        mock_psutil.process_iter.return_value = [mock_proc1, mock_proc2]
        response = self.client.get('/processes')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'test_proc1', response.data)
        self.assertIn(b'12.3%', response.data)
        self.assertIn(b'test_proc2', response.data)
        self.assertIn(b'0.5%', response.data)
        mock_psutil.process_iter.assert_called_once_with(['pid', 'name', 'username', 'cpu_percent', 'memory_percent'])

    @patch('app.CAMERA_AVAILABLE', True)
    @patch('app.picam2', create=True) 
    @patch('app.io.BytesIO')
    def test_camera_feed_real_mode_picam2(self, mock_BytesIO, mock_picam2_instance, mock_camera_available_flag): 
        with patch('app.camera', None): 
            mock_buffer = MagicMock(); mock_buffer.getvalue.return_value = b'fake_picam2_jpeg_bytes'
            mock_BytesIO.return_value = mock_buffer
            mock_picam2_instance.started = False 
            mock_picam2_instance.create_still_configuration.return_value = {} 
            response = self.client.get('/camera_feed')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.mimetype, 'image/jpeg')
            self.assertEqual(response.data, b'fake_picam2_jpeg_bytes')
            mock_picam2_instance.capture_file.assert_called_once_with(mock_buffer, format='jpeg')

    @patch('app.CAMERA_AVAILABLE', True)
    @patch('app.camera', create=True) 
    @patch('app.io.BytesIO')
    def test_camera_feed_real_mode_picamera(self, mock_BytesIO, mock_picamera_instance, mock_camera_available_flag): 
        with patch('app.picam2', None):
            mock_buffer = MagicMock(); mock_buffer.getvalue.return_value = b'fake_picamera_jpeg_bytes'
            mock_BytesIO.return_value = mock_buffer
            mock_picamera_instance.resolution = (0,0) 
            response = self.client.get('/camera_feed')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.mimetype, 'image/jpeg')
            self.assertEqual(response.data, b'fake_picamera_jpeg_bytes')
            mock_picamera_instance.capture.assert_called_once_with(mock_buffer, format='jpeg', use_video_port=True)

    @patch('app.subprocess.run')
    def test_ssh_command_real_mode(self, mock_subprocess_run): # This test is in RealModeAppTests but doesn't rely on the class patches
        mock_process = MagicMock()
        mock_process.stdout = "Real command output"
        mock_process.stderr = ""
        mock_process.returncode = 0
        mock_subprocess_run.return_value = mock_process
        with self.client.session_transaction() as sess:
            sess['last_command'] = ''; sess['last_command_output'] = ''; sess['last_command_error'] = ''
        response = self.client.post('/ssh/command', data={'command': 'ls -l mydir'}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Real command output", response.data)
        mock_subprocess_run.assert_called_with(
            ['ls', '-l', 'mydir'], capture_output=True, text=True, timeout=10, check=False, cwd=str(Path.home())
        )

    @patch('app.FILE_MANAGER_REAL_MODE', True)
    @patch('app.Path')
    @patch('app.os.path.exists') 
    @patch('app.os.access') 
    def test_file_manager_real_mode_list_basic(self, mock_os_access, mock_os_path_exists, mock_Path_class, mock_file_manager_real_mode_flag): 
        mock_os_access.return_value = True 
        mock_home_path_instance = MagicMock(spec=Path); mock_home_path_instance.name = "RaspControll_files" 
        mock_Path_class.home.return_value = mock_home_path_instance
        mock_base_dir_instance = MagicMock(spec=Path)
        mock_home_path_instance.joinpath.return_value = mock_base_dir_instance 
        mock_base_dir_instance.resolve.return_value = mock_base_dir_instance 
        mock_base_dir_instance.mkdir.return_value = None 
        mock_base_dir_instance.iterdir.return_value = [] 
        mock_resolved_current_path = MagicMock(spec=Path)
        mock_base_dir_instance.joinpath.side_effect = lambda p: mock_resolved_current_path if p == '' else mock_base_dir_instance.joinpath(p) 
        mock_resolved_current_path.resolve.return_value = mock_resolved_current_path
        with patch('app.os.path.commonpath') as mock_commonpath:
            mock_commonpath.return_value = mock_base_dir_instance 
            mock_file_item = MagicMock(spec=Path); mock_file_item.name = "testfile.txt"; mock_file_item.is_dir.return_value = False
            mock_file_item.is_file.return_value = True; mock_file_item.stat.return_value = MagicMock(st_size=100, st_mtime=datetime.datetime.now().timestamp())
            mock_dir_item = MagicMock(spec=Path); mock_dir_item.name = "testdir"; mock_dir_item.is_dir.return_value = True
            mock_dir_item.is_file.return_value = False
            mock_resolved_current_path.iterdir.return_value = [mock_file_item, mock_dir_item]
            response = self.client.get('/file-manager/')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'testfile.txt', response.data)
            self.assertIn(b'testdir', response.data)
            self.assertIn(b'100 B', response.data) 
            self.assertIn(b'File Manager', response.data)

if __name__ == '__main__':
    unittest.main()
