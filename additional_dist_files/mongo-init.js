db.createUser(
        {
            user: "JOTUser",
            pwd: "YOURPASSWORDHERE",
            roles: [
                {
                    role: "readWrite",
                    db: "production_testing"
                }
            ]
        }
);
