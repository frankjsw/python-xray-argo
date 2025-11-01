import os
import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class KatabumpAppWaker:
    """
    针对Katabump应用的自动唤醒脚本
    """
    
    # 配置class类常量
    APP_URL = os.environ.get("KATABUMP_APP_URL", "")
    INITIAL_WAIT_TIME = 10  # 网站初始加载等待时间
    POST_CLICK_WAIT_TIME = 20  # 点击唤醒按钮后等待时间
    BUTTON_TEXT = "Yes, get this app back up!"
    BUTTON_SELECTOR = "//button[text()='Yes, get this app back up!']"
    
    def __init__(self):
        self.driver = None
        self.setup_driver()
    
    def setup_driver(self):
        # 设置Chrome驱动选项
        logger.info("⚙️ 正在设置Chrome驱动...")
        chrome_options = Options()
        
        if os.getenv('GITHUB_ACTIONS'):
            logger.info("⚙️ 检测到CI环境，启用headless模式。")
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')

        # 通用配置：反爬虫设置
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            logger.info("✅ Chrome驱动设置完成。")
        except Exception as e:
            logger.error(f"❌ 驱动初始化失败: {e}")
            raise

    def wait_for_element_clickable(self, by, value, timeout=10):
        """等待元素可点击"""
        return WebDriverWait(self.driver, timeout).until(
            EC.element_to_be_clickable((by, value))
        )
    
    def find_and_click_button(self, context_description="主页面"):
        """查找并点击唤醒按钮，支持 iframe 内查找"""
        logger.info(f"🔍 尝试在 {context_description} 查找唤醒按钮: '{self.BUTTON_TEXT}'")
        
        try:
            # 使用 WebDriverWait 确保按钮出现并可点击
            button = self.wait_for_element_clickable(By.XPATH, self.BUTTON_SELECTOR, 5)
            
            # 确保按钮可见且可用
            if button.is_displayed() and button.is_enabled():
                button.click()
                logger.info(f"✅ 在 {context_description} 成功点击唤醒按钮。")
                return True
            else:
                logger.warning(f"⚠️ 在 {context_description} 找到按钮，但按钮不可点击或不可见。")
                return False

        except TimeoutException:
            logger.info(f"❌ 在 {context_description} 规定时间内未找到唤醒按钮。")
            return False
        except NoSuchElementException:
             logger.info(f"❌ 在 {context_description} 未找到唤醒按钮。")
             return False
        except Exception as e:
            logger.error(f"❌ 在 {context_description} 点击按钮时发生异常: {e}")
            return False

    def is_app_woken_up(self):
        """检查应用是否已唤醒（即按钮是否消失）"""
        logger.info("🧐 检查唤醒按钮是否已消失...")
        
        # 1. 检查主页面
        self.driver.switch_to.default_content()
        try:
            # 等待5秒，检查按钮是否存在
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.XPATH, self.BUTTON_SELECTOR))
            )
            logger.info("❌ 唤醒按钮仍在主页面显示。应用未唤醒。")
            return False
        except TimeoutException:
            logger.info("✅ 唤醒按钮在主页面已消失。")
            
        # 2. 检查 iframe（Katabump 应用有时会嵌入在 iframe 中）
        try:
            iframe = self.driver.find_element(By.TAG_NAME, "iframe")
            self.driver.switch_to.frame(iframe)
            
            # 在 iframe 内检查按钮是否消失
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.XPATH, self.BUTTON_SELECTOR))
            )
            
            self.driver.switch_to.default_content() # 切回主页面
            logger.info("❌ 唤醒按钮在 iframe 内仍显示。应用未唤醒。")
            return False
        except (NoSuchElementException, TimeoutException):
            self.driver.switch_to.default_content() # 确保切回主页面
            logger.info("✅ 应用唤醒成功，唤醒按钮已消失。")
            return True
        except Exception as e:
             # 出现其他异常，可能是网络问题
            self.driver.switch_to.default_content()
            logger.error(f"❌ 检查唤醒状态时发生异常: {e}")
            return False


    def wakeup_app(self):
        """执行唤醒流程"""
        if not self.APP_URL:
            raise Exception("⚠️ 环境变量 KATABUMP_APP_URL 未配置。")
            
        logger.info(f"👉 访问应用URL: {self.APP_URL}")
        self.driver.get(self.APP_URL)
        
        logger.info(f"⏳ 等待初始页面加载 {self.INITIAL_WAIT_TIME} 秒...")
        time.sleep(self.INITIAL_WAIT_TIME)
        
        click_success = False
        
        # 尝试步骤 1: 在主页面查找并点击
        click_success = self.find_and_click_button("主页面")
        
        # 尝试步骤 2: 查找 iframe 并切换，然后在 iframe 内查找并点击
        if not click_success:
            logger.info("👉 主页面未找到按钮，尝试进入 iframe 查找...")
            try:
                # 查找页面上的 iframe
                iframe = self.driver.find_element(By.TAG_NAME, "iframe")
                try:
                    self.driver.switch_to.frame(iframe)
                    logger.info("✅ 成功切换到 iframe。")
                    click_success = self.find_and_click_button("iframe内部")
                    
                finally:
                    # 确保切回主页面进行后续检查
                    self.driver.switch_to.default_content()
                
            except NoSuchElementException:
                logger.info("❌ 页面未找到 iframe 元素。")
            except Exception as e:
                logger.error(f"❌ 查找或切换到 iframe 时出错: {e}")
                
        if not click_success:
            # 如果主页面和 iframe 都没有找到并点击成功
            if self.is_app_woken_up():
                return True, "✅ 应用已处于唤醒状态，无需操作。" 
            else:
                raise Exception("⚠️ 找不到或无法点击唤醒按钮。请检查应用URL和按钮选择器是否正确。")
        
        # 步骤 3: 点击成功后等待
        logger.info(f"⏳ 成功点击唤醒按钮。等待应用启动 {self.POST_CLICK_WAIT_TIME} 秒...")
        time.sleep(self.POST_CLICK_WAIT_TIME)
        
        # 步骤 4: 检查唤醒结果 (按钮是否消失)
        if self.is_app_woken_up():
            return True, "✅ 应用唤醒成功！"
        else:
            raise Exception("❌ 唤醒操作已执行，但唤醒按钮在等待后仍然存在。应用可能未能成功启动。")

    def run(self):
        """执行流程，返回 (success: bool, result_message: str)"""
        result = "未知错误"
        success = False
        try:
            logger.info("🚀 Katabump应用唤醒脚本开始执行...")
            success, result = self.wakeup_app() 
            return success, result
                
        except Exception as e:
            error_msg = f"❌ 脚本执行失败: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        
        finally:
            if self.driver:
                logger.info("🧹 关闭Chrome驱动...")
                self.driver.quit()

def main():
    """主函数"""
    app_url = os.environ.get("KATABUMP_APP_URL", "未配置，将使用默认值(空)")
    logger.info(f"配置的应用 URL: {app_url}")
    
    waker = None
    try:
        waker = KatabumpAppWaker()
        success, result = waker.run()
        logger.info(f"🚀 最终结果: {result}")
        
        if success:
            logger.info("✅ 脚本执行完毕，应用唤醒流程成功。")
            exit(0)
        else:
            logger.error(f"❌ 脚本执行完毕，应用唤醒流程失败。")
            exit(0)
            
    except Exception as e:
        logger.error(f"❌ 脚本主函数出错: {e}")
        exit(1)

if __name__ == "__main__":
    main()
