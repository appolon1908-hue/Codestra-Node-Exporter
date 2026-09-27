package main

import (
	"fmt"
	"net"
	"os"
	"time"
)

const defaultAddress = "127.0.0.1:9100"

func main() {
	address := os.Getenv("NODE_EXPORTER_HEALTHCHECK_ADDRESS")
	if address == "" {
		address = defaultAddress
	}

	connection, err := net.DialTimeout("tcp", address, 5*time.Second)
	if err != nil {
		fmt.Fprintf(os.Stderr, "node exporter listener check failed: %v\n", err)
		os.Exit(1)
	}
	_ = connection.Close()
}
