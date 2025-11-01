import os
import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class KatabumpAppWaker:
    """
    针对Katabump应用的自动唤醒脚本（修改为定位并点击包含 class Button___StyledSpan-sc-1qu1gou-2 且文本 시간추가 的按钮）
    """
    
    # 配置class类常量
    APP_URL = os.environ.get("KATABUMP_APP_URL", "")
    INITIAL_WAIT_TIME = 10  # 网站初始加载等待时间
    POST_CLICK_WAIT_TIME = 20  # 点击唤醒按钮后等待时间

    # 新的目标：定位到 <span class="Button___StyledSpan-sc-1qu1gou-2">시간추가</span>
    BUTTON_TEXT = "시간추가"
    # 首先尝试点击包含该 span 的最近 button（更稳健）
    BUTTON_SELECTOR = ("//span[contains(@class,'Button___StyledSpan-sc-1qu1gou-2') "
                       "and normalize-space(text())='시간추가']/ancestor::button[1]")
    # 备用：如果没有 button，则直接定位 span
    SPAN_SELECTOR = ("//span[contains(@class,'Button___StyledSpan-sc-1qu1gou-2') "
                     "and normalize-space(text())='시간추가']")

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
            # 隐藏 webdriver 标志（注意：仅对反检测有小幅帮助）
            try:
                self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            except Exception:
                pass
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
        """查找并点击唤醒按钮（支持先找祖先 button，再找 span）"""
        logger.info(f"🔍 尝试在 {context_description} 查找唤醒按钮/元素: '{self.BUTTON_TEXT}'")
        
        # 尝试 1：定位祖先 button（如果存在）
        try:
            button = self.wait_for_element_clickable(By.XPATH, self.BUTTON_SELECTOR, 5)
            # 确保按钮可见且可用
            if button and button.is_displayed() and button.is_enabled():
                button.click()
                logger.info(f"✅ 在 {context_description} 成功点击祖先 button（通过 span 定位）。")
                return True
            else:
                logger.warning(f"⚠️ 在 {context_description} 找到祖先 button，但不可点击或不可见。")
        except TimeoutException:
            logger.info(f"❌ 在 {context_description} 规定时间内未找到祖先 button。尝试直接定位 span...")
        except NoSuchElementException:
            logger.info(f"❌ 在 {context_description} 未找到祖先 button。尝试直接定位 span...")
        except WebDriverException as e:
            logger.error(f"❌ 在 {context_description} 点击祖先 button 时异常: {e}")

        # 尝试 2：直接定位并点击 span 元素（如果确实没有 button）
        try:
            span_el = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, self.SPAN_SELECTOR))
            )
            if span_el and span_el.is_displayed() and span_el.is_enabled():
                try:
                    span_el.click()
                    logger.info(f"✅ 在 {context_description} 成功点击 span 元素。")
                    return True
                except WebDriverException:
                    # 有时 span 不是可点击目标，尝试用 JS 点击
                    try:
                        self.driver.execute_script("arguments[0].click();", span_el)
                        logger.info(f"✅ 在 {context_description} 使用 JS 点击 span 成功。")
                        return True
                    except Exception as e:
                        logger.error(f"❌ 使用 JS 点击 span 失败: {e}")
                        return False
            else:
                logger.warning(f"⚠️ 在 {context_description} 找到 span，但不可点击或不可见。")
                return False
        except TimeoutException:
            logger.info(f"❌ 在 {context_description} 规定时间内未找到 span 元素。")
            return False
        except Exception as e:
            logger.error(f"❌ 在 {context_description} 定位/点击 span 时发生异常: {e}")
            return False

    def is_app_woken_up(self):
        """检查应用是否已唤醒（即按钮是否消失）"""
        logger.info("🧐 检查唤醒按钮是否已消失...")
        
        # 1. 检查主页面
        self.driver.switch_to.default_content()
        try:
            # 等待5秒，检查按钮是否存在（这里用 span 选择器作为存在判断）
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.XPATH, self.SPAN_SELECTOR))
            )
            logger.info("❌ 唤醒元素（span）仍在主页面显示。应用可能未唤醒。")
            return False
        except TimeoutException:
            logger.info("✅ 唤醒元素在主页面已消失或未找到。")
            
        # 2. 检查 iframe（应用可能嵌入在 iframe 中）
        try:
            iframe = self.driver.find_element(By.TAG_NAME, "iframe")
            self.driver.switch_to.frame(iframe)
            
            # 在 iframe 内检查 span 是否存在
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.XPATH, self.SPAN_SELECTOR))
            )
            
            self.driver.switch_to.default_content() # 切回主页面
            logger.info("❌ 唤醒元素在 iframe 内仍显示。应用未唤醒。")
            return False
        except (NoSuchElementException, TimeoutException):
            # 如果 iframe 中没有该元素，认为唤醒成功（或元素已消失）
            self.driver.switch_to.default_content() # 确保切回主页面
            logger.info("✅ 应用唤醒成功或唤醒元素已消失。")
            return True
        except Exception as e:
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
            logger.info("👉 主页面未找到目标元素，尝试进入 iframe 查找...")
            try:
                # 查找页面上的 iframe（尝试多个 iframe）
                iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
                if not iframes:
                    logger.info("❌ 页面未找到 iframe 元素。")
                else:
                    for idx, iframe in enumerate(iframes):
                        try:
                            logger.info(f"🔁 尝试切换到第 {idx+1} 个 iframe。")
                            self.driver.switch_to.frame(iframe)
                            logger.info("✅ 成功切换到 iframe。")
                            click_success = self.find_and_click_button(f"iframe内部 (index {idx})")
                            self.driver.switch_to.default_content()
                            if click_success:
                                break
                        except Exception as e_inner:
                            logger.warning(f"⚠️ 切换/操作 iframe (index {idx}) 时出错: {e_inner}")
                            self.driver.switch_to.default_content()
            except Exception as e:
                logger.error(f"❌ 查找或切换到 iframe 时出错: {e}")
                
        if not click_success:
            # 如果主页面和 iframe 都没有找到并点击成功
            if self.is_app_woken_up():
                return True, "✅ 应用已处于唤醒状态，无需操作。" 
            else:
                raise Exception("⚠️ 找不到或无法点击目标唤醒元素（시간추가）。请检查应用URL和选择器是否正确。")
        
        # 步骤 3: 点击成功后等待
        logger.info(f"⏳ 成功点击目标元素。等待应用启动 {self.POST_CLICK_WAIT_TIME} 秒...")
        time.sleep(self.POST_CLICK_WAIT_TIME)
        
        # 步骤 4: 检查唤醒结果 (元素是否消失)
        if self.is_app_woken_up():
            return True, "✅ 应用唤醒成功！"
        else:
            raise Exception("❌ 唤醒操作已执行，但目标元素在等待后仍然存在。应用可能未能成功启动。")

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
