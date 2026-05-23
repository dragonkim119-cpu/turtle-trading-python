import 'package:flutter/material.dart';
import '../services/api_service.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});
  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final _urlCtrl = TextEditingController();
  bool _healthy = false;
  bool _checking = false;

  @override
  void initState() {
    super.initState();
    _loadUrl();
  }

  Future<void> _loadUrl() async {
    final url = await ApiService.getBaseUrl();
    _urlCtrl.text = url;
    _checkHealth();
  }

  Future<void> _checkHealth() async {
    setState(() => _checking = true);
    final ok = await ApiService.checkHealth();
    setState(() { _healthy = ok; _checking = false; });
  }

  Future<void> _save() async {
    await ApiService.setBaseUrl(_urlCtrl.text.trim());
    await _checkHealth();
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(_healthy ? '서버 연결 성공' : '서버 연결 실패')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('설정')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('백엔드 서버 URL',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
            const SizedBox(height: 8),
            TextField(
              controller: _urlCtrl,
              decoration: const InputDecoration(
                border: OutlineInputBorder(),
                hintText: 'http://192.168.0.x:8000',
                helperText: '같은 WiFi: PC의 IP 주소 입력 / 에뮬레이터: http://10.0.2.2:8000',
              ),
              keyboardType: TextInputType.url,
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                ElevatedButton(onPressed: _save, child: const Text('저장 & 연결 확인')),
                const SizedBox(width: 12),
                if (_checking) const SizedBox(width: 20, height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2))
                else Row(
                  children: [
                    Icon(
                      _healthy ? Icons.check_circle : Icons.cancel,
                      color: _healthy ? Colors.green : Colors.red,
                    ),
                    const SizedBox(width: 4),
                    Text(_healthy ? '연결됨' : '연결 안됨'),
                  ],
                ),
              ],
            ),
            const SizedBox(height: 32),
            const Divider(),
            const SizedBox(height: 16),
            const Text('터틀 트레이딩 시스템',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
            const SizedBox(height: 8),
            _infoRow('System 1', '20일 돌파 진입 / 10일 청산'),
            _infoRow('System 2', '55일 돌파 진입 / 20일 청산'),
            _infoRow('포지션 사이징', '계좌 × 1% ÷ ATR(20)'),
            _infoRow('피라미딩', '0.5 ATR 간격, 최대 4유닛'),
            _infoRow('손절', '진입가 ± 2 × ATR'),
            const SizedBox(height: 40),
          ],
        ),
      ),
    );
  }

  Widget _infoRow(String label, String value) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(
              width: 110,
              child: Text(label,
                  style: TextStyle(color: Colors.grey[700], fontWeight: FontWeight.w500)),
            ),
            Expanded(child: Text(value)),
          ],
        ),
      );
}
