package android.os;
/** Original authored retained graph shape plus an explicit synthetic CE query. */
public class UserManager {
 private final IUserManager mService;
 public UserManager(){mService=null;}
 public UserManager(IUserManager service){model.Forbidden.constructions++;mService=service;}
 public int getUserSerialNumber(int user){model.Forbidden.calls++;throw new AssertionError("original queries forbidden");}
 public boolean isUserUnlocked(UserHandle user){if(user==null||user.getIdentifier()!=0)throw new AssertionError("user0 only");model.LinkModel.unlockReads++;return model.LinkModel.unlocked;}
}
