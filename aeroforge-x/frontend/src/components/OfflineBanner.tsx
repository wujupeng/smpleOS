import { useTranslation } from 'react-i18next'
import { Alert } from 'antd'
import { WifiOutlined } from '@ant-design/icons'
import { useNetworkStatus } from '../hooks/useTouchGesture'

export function OfflineBanner() {
  const isOnline = useNetworkStatus()
  const { t } = useTranslation()

  if (isOnline) return null

  return (
    <Alert
      type="warning"
      message={t('common.offlineWarning', '当前处于离线模式，部分功能不可用')}
      icon={<WifiOutlined />}
      showIcon
      style={{ marginBottom: 12, borderRadius: 4 }}
      banner
    />
  )
}